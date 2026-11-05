import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'

import { friendlyMessage } from '@/shared/api/errors'

import type { NewTicketValues } from '../model/schemas'
import { ticketKeys, ticketsApi } from '../model/ticketsApi'
import type { Ticket, TimelineEntry } from '../model/types'

const RECONNECT_MS = 2000
const FINAL = new Set(['answered', 'failed'])

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
      queryClient.setQueryData(ticketKeys.detail(ticket.public_id), ticket)
      void queryClient.invalidateQueries({ queryKey: ticketKeys.list() })
      navigate(`/tickets/${ticket.public_id}`)
    },
    onError: (error) => toast.error(friendlyMessage(error)),
  })
}

function describe(event: string, data: Record<string, unknown>): Omit<TimelineEntry, 'id' | 'at'> | null {
  switch (event) {
    case 'processing':
      return { kind: 'status', text: 'The assistant picked up your ticket' }
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
export function useTicketStream(ticket: Ticket | undefined) {
  const queryClient = useQueryClient()
  const [timeline, setTimeline] = useState<TimelineEntry[]>([])
  const [live, setLive] = useState(false)
  const id = ticket?.public_id
  const finished = !ticket || FINAL.has(ticket.status)

  useEffect(() => {
    if (!id || finished) return
    const controller = new AbortController()
    let lastEventId: string | undefined
    let done = false

    const onEvent = (event: string, raw: unknown, eventId: string | undefined) => {
      if (eventId) lastEventId = eventId
      const data = (raw ?? {}) as Record<string, unknown>
      const entry = describe(event, data)
      if (entry) setTimeline((items) => [...items, { ...entry, id: eventId ?? `${event}-${items.length}`, at: Date.now() }])
      if (FINAL.has(event) || event === 'approval_required') {
        done = event !== 'approval_required'
        void queryClient.invalidateQueries({ queryKey: ticketKeys.all })
      }
    }

    const run = async () => {
      while (!controller.signal.aborted && !done) {
        setLive(true)
        try {
          await ticketsApi.stream(id, controller.signal, onEvent, lastEventId)
        } catch {
          if (controller.signal.aborted) return
        }
        setLive(false)
        if (!done) await new Promise((resolve) => setTimeout(resolve, RECONNECT_MS))
      }
    }
    void run()
    return () => controller.abort()
  }, [id, finished, queryClient])

  return { timeline, live: live && !finished }
}
