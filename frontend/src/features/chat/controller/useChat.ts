import { useMutation } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'

import { friendlyMessage } from '@/shared/api/errors'
import { newId } from '@/shared/lib/format'

import { chatApi } from '../model/chatApi'
import { useChatStore } from '../model/chatStore'
import type { ChatMessage, ChatOut, ChatStreamEvent, TurnMeta } from '../model/types'

const EMPTY_META: TurnMeta = { routes: [], toolCalls: [], blockedReason: null, guardRewrites: 0 }

function metaFromChatOut(out: ChatOut): TurnMeta {
  return {
    routes: out.routes,
    toolCalls: out.tool_calls,
    blockedReason: out.blocked_reason,
    guardRewrites: out.output_retries,
    latencyMs: out.latency_ms,
    tokens: out.tokens,
    llmCalls: out.llm_calls,
  }
}

/** One conversation: streams a reply token by token and handles confirm/cancel of a pending write. */
export function useChat(conversationId: string) {
  const conversation = useChatStore((s) => s.conversations[conversationId])
  const { ensure, addMessage, patchMessage, setPending } = useChatStore.getState()
  const [streaming, setStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  // Tokens arrive faster than the screen repaints; they are batched into one store update per animation frame.
  const bufferRef = useRef('')
  const frameRef = useRef<number | null>(null)

  useEffect(() => {
    ensure(conversationId)
    return () => abortRef.current?.abort()
  }, [conversationId, ensure])

  const send = async (text: string) => {
    const message = text.trim()
    if (!message || streaming) return
    const replyId = newId('m')
    addMessage(conversationId, { id: newId('m'), role: 'user', text: message, status: 'done', createdAt: Date.now() })
    addMessage(conversationId, { id: replyId, role: 'assistant', text: '', status: 'streaming', createdAt: Date.now(), meta: { ...EMPTY_META } })

    const patch = (fn: (m: ChatMessage) => Partial<ChatMessage>) => patchMessage(conversationId, replyId, fn)
    const patchMeta = (fn: (meta: TurnMeta) => Partial<TurnMeta>) => patch((m) => ({ meta: { ...EMPTY_META, ...m.meta, ...fn({ ...EMPTY_META, ...m.meta }) } }))
    const flush = () => {
      frameRef.current = null
      const chunk = bufferRef.current
      bufferRef.current = ''
      if (chunk) patch((m) => ({ text: m.text + chunk }))
    }
    const discardBuffer = () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current)
      frameRef.current = null
      bufferRef.current = ''
    }

    const onEvent = (e: ChatStreamEvent) => {
      switch (e.event) {
        case 'token':
          bufferRef.current += e.data.text
          frameRef.current ??= requestAnimationFrame(flush)
          break
        case 'reset':
          discardBuffer()
          patch(() => ({ text: '' }))
          patchMeta((meta) => ({ guardRewrites: meta.guardRewrites + 1 }))
          break
        case 'replace':
          discardBuffer()
          patch(() => ({ text: e.data.text }))
          break
        case 'routing':
          patchMeta(() => ({ routes: e.data.domains }))
          break
        case 'guardrail':
          patchMeta(() => ({ blockedReason: e.data.blocked_reason }))
          break
        case 'tool_call':
          patchMeta((meta) => ({ toolCalls: [...meta.toolCalls, e.data] }))
          break
        case 'confirmation_required':
          discardBuffer()
          patch(() => ({ text: e.data.reply }))
          setPending(conversationId, e.data.pending_action)
          break
        case 'done':
          flush()
          patch(() => ({ status: 'done' }))
          patchMeta(() => ({ latencyMs: e.data.latency_ms }))
          break
        case 'error':
          discardBuffer()
          patch(() => ({ status: 'error', text: e.data.message }))
          break
      }
    }

    const controller = new AbortController()
    abortRef.current = controller
    setStreaming(true)
    try {
      await chatApi.stream(conversationId, message, controller.signal, onEvent)
      flush()
      patch((m) => (m.status === 'streaming' ? { status: 'done' } : {}))
    } catch (error) {
      discardBuffer()
      const stopped = controller.signal.aborted
      patch((m) => ({ status: stopped ? 'done' : 'error', text: stopped ? m.text || '_Stopped._' : friendlyMessage(error) }))
    } finally {
      abortRef.current = null
      setStreaming(false)
    }
  }

  const stop = () => abortRef.current?.abort()

  const confirm = useMutation({
    mutationFn: (approved: boolean) => chatApi.confirm(conversationId, approved),
    onSuccess: (out) => {
      setPending(conversationId, out.status === 'confirmation_required' ? out.pending_action : null)
      addMessage(conversationId, { id: newId('m'), role: 'assistant', text: out.reply, status: 'done', createdAt: Date.now(), meta: metaFromChatOut(out) })
    },
    onError: (error) => toast.error(friendlyMessage(error)),
  })

  return {
    messages: conversation?.messages ?? [],
    pending: conversation?.pending ?? null,
    streaming,
    send,
    stop,
    confirm,
  }
}
