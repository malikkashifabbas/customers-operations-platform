import { http } from '@/shared/api/http'
import { streamSse, type SseHandler } from '@/shared/api/sse'

import type { Ticket } from './types'

export const ticketsApi = {
  list: () => http.get<Ticket[]>('/tickets/'),
  get: (id: string) => http.get<Ticket>(`/tickets/${id}`),
  create: (body: { subject: string; body: string }) => http.post<Ticket>('/tickets/', body),
  stream: (id: string, signal: AbortSignal, onEvent: SseHandler, lastEventId?: string) =>
    streamSse(`/tickets/${id}/stream`, { method: 'GET', signal, onEvent, lastEventId }),
}

export const ticketKeys = {
  all: ['tickets'] as const,
  list: () => [...ticketKeys.all, 'list'] as const,
  detail: (id: string) => [...ticketKeys.all, 'detail', id] as const,
}
