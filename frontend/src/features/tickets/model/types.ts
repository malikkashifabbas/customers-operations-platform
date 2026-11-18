export type TicketStatus = 'open' | 'waiting_approval' | 'answered' | 'failed'

export type RefundRequest = { type: 'refund_approval'; order_number: string; amount: string; reason: string }

export type Ticket = {
  public_id: string
  subject: string
  body: string
  status: TicketStatus
  reply: string
  approval_request: RefundRequest | null
  created_at: string
  answered_at: string | null
}

export type TicketMessage = {
  public_id: string
  author: 'customer' | 'assistant'
  body: string
  created_at: string
}

/** GET /api/tickets/{id}: the ticket plus its whole conversation. */
export type TicketDetail = Ticket & { messages: TicketMessage[] }

/** One line of the live timeline built from GET /api/tickets/{id}/stream. */
export type TimelineEntry = { id: string; kind: 'status' | 'routing' | 'tool' | 'approval' | 'final' | 'error' | 'customer'; text: string; at: number }
