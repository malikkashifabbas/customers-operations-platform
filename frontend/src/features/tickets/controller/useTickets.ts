import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'

import { friendlyMessage } from '@/shared/api/errors'

import type { NewTicketValues } from '../model/schemas'
import { ticketKeys, ticketsApi } from '../model/ticketsApi'
import type { TicketDetail, TicketStatus, TimelineEntry } from '../model/types'

const RECONNECT_MS = 2000
const FINAL_EVENTS = new Set(['answered', 'failed'])
const SETTLED: ReadonlySet<TicketStatus> = new Set(['answered', 'failed'])

export function useTickets() {
  return useQuery({ queryKey: ticketKeys.list(), queryFn: ticketsApi.list, staleTime: 15_000 })
}

export function useTicket(id: string) {
  return useQuery({ queryKey: ticketKeys.detail(id), queryFn: () => ticketsApi.get(id) })
}

export function useCreateTicket() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  return useMutation({
    mutationFn: (values: NewTicketValues) => ticketsApi.create(values),
    onSuccess: (ticket) => {
      const firstMessage = { public_id: `${ticket.public_id}-first`, author: 'customer' as const, body: ticket.body, created_at: ticket.created_at }
      queryClient.setQueryData<TicketDetail>(ticketKeys.detail(ticket.public_id), { ...ticket, messages: [firstMessage] })
      void queryClient.invalidateQueries({ queryKey: ticketKeys.list() })
      navigate(`/tickets/${ticket.public_id}`)
    },
    onError: (error) => toast.error(friendlyMessage(error)),
  })
}

export function useReplyToTicket(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: string) => ticketsApi.reply(id, body),
    // The 202 already carries the reopened ticket: status "open" restarts the live stream without another request.
    onSuccess: (ticket) => {
      queryClient.setQueryData(ticketKeys.detail(id), ticket)
      void queryClient.invalidateQueries({ queryKey: ticketKeys.list() })
    },
    onError: (error) => toast.error(friendlyMessage(error)),
  })
}

function describe(event: string, data: Record<string, unknown>): Omit<TimelineEntry, 'id' | 'at'> | null {
  switch (event) {
    case 'processing':
      return { kind: 'status', text: 'The assistant picked up your ticket' }
    case 'customer_message':
      return { kind: 'customer', text: 'You replied' }
    case 'routing':
      return { kind: 'routing', text: `Specialists: ${(data.domains as string[]).join(', ')}` }
    case 'tool_call':
      return { kind: 'tool', text: `Checked: ${String(data.name).replaceAll('_', ' ')}` }
    case 'approval_required':
      return { kind: 'approval', text: `Refund for ${String(data.order_number)} sent to staff for approval` }
    case 'approval_decided':
      return { kind: 'approval', text: data.approved ? 'Staff approved the refund' : 'Staff declined the refund' }
    case 'answered':
      return { kind: 'final', text: 'Answered' }
    case 'failed':
      return { kind: 'error', text: 'The assistant could not finish this ticket' }
    default:
      return null
  }
}

/** Live progress of one ticket; reconnects with Last-Event-ID so nothing is missed or shown twice. */
export function useTicketStream(ticket: TicketDetail | undefined) {
  const queryClient = useQueryClient()
  const [timeline, setTimeline] = useState<TimelineEntry[]>([])
  const [live, setLive] = useState(false)
  // Kept across runs: after a follow-up the stream resumes after the last event instead of replaying the old answer.
  const lastEventIdRef = useRef<string | undefined>(undefined)
  const statusRef = useRef<TicketStatus | undefined>(ticket?.status)
  const id = ticket?.public_id
  const settled = !ticket || SETTLED.has(ticket.status)

  useEffect(() => {
    statusRef.current = ticket?.status
  }, [ticket?.status])

  useEffect(() => {
    if (!id || settled) return
    const controller = new AbortController()

    const onEvent = (event: string, raw: unknown, eventId: string | undefined) => {
      if (eventId) lastEventIdRef.current = eventId
      const data = (raw ?? {}) as Record<string, unknown>
      const entry = describe(event, data)
      // The same Redis event can arrive twice (dev double-mount, reconnect replay); its stream id shows it once.
      if (entry) setTimeline((items) => (eventId && items.some((i) => i.id === eventId) ? items : [...items, { ...entry, id: eventId ?? `${event}-${items.length}`, at: Date.now() }]))
      // A refetch tells whether this final event is the newest one; the status change then stops the stream.
      if (FINAL_EVENTS.has(event) || event === 'approval_required') void queryClient.invalidateQueries({ queryKey: ticketKeys.all })
    }

    const run = async () => {
      while (!controller.signal.aborted) {
        setLive(true)
        try {
          await ticketsApi.stream(id, controller.signal, onEvent, lastEventIdRef.current)
        } catch {
          if (controller.signal.aborted) return
        }
        setLive(false)
        if (statusRef.current && SETTLED.has(statusRef.current)) return
        await new Promise((resolve) => setTimeout(resolve, RECONNECT_MS))
      }
    }
    void run()
    return () => controller.abort()
  }, [id, settled, queryClient])

  return { timeline, live: live && !settled }
}
