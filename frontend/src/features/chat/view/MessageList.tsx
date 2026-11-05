import { MessagesSquare } from 'lucide-react'
import { useEffect, useRef } from 'react'

import type { ChatMessage } from '../model/types'
import { MessageBubble } from './MessageBubble'

const SUGGESTIONS = [
  'List my orders',
  'What is your return window?',
  'Open a ticket for ORD-1001: the item arrived damaged',
  'Cancel my pending order',
  'Do you have my account details?',
  'Do you deliver to Dubai?',
]

export function MessageList({ messages, onSuggestion }: { messages: ChatMessage[]; onSuggestion: (text: string) => void }) {
  const endRef = useRef<HTMLDivElement>(null)
  const last = messages.at(-1)

  // Follow the reply while it grows, but only if the user is already near the bottom.
  useEffect(() => {
    const end = endRef.current
    const scroller = end?.parentElement
    if (!end || !scroller) return
    const nearBottom = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 160
    if (nearBottom || last?.role === 'user') end.scrollIntoView({ block: 'end' })
  }, [last?.text, last?.role, messages.length])

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center overflow-y-auto px-4 py-10 text-center">
        <span className="grid size-14 place-items-center rounded-2xl bg-brand-50 text-primary dark:bg-brand-950">
          <MessagesSquare className="size-7" />
        </span>
        <h2 className="mt-4 text-lg font-semibold">How can we help today?</h2>
        <p className="mt-1 max-w-md text-sm text-fg-muted">Ask about your orders, your account or our policies. Anything that changes data waits for your confirmation.</p>
        <div className="mt-6 grid w-full max-w-xl gap-2 sm:grid-cols-2">
          {SUGGESTIONS.map((text) => (
            <button
              key={text}
              type="button"
              onClick={() => onSuggestion(text)}
              className="rounded-xl border border-line bg-surface px-4 py-3 text-left text-sm text-fg transition-colors hover:border-brand-300 hover:bg-brand-50 dark:hover:bg-brand-950"
            >
              {text}
            </button>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6" aria-live="polite" aria-relevant="additions">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
      </div>
      <div ref={endRef} />
    </div>
  )
}
