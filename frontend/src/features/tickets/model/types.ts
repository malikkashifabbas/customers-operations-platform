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

/** One line of the live timeline built from GET /api/tickets/{id}/stream. */
export type TimelineEntry = { id: string; kind: 'status' | 'routing' | 'tool' | 'approval' | 'final' | 'error'; text: string; at: number }
