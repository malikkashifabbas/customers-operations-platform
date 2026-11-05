import type { RefundRequest, TicketStatus } from '@/features/tickets/model/types'

export type StaffTicket = {
  public_id: string
  subject: string
  body: string
  status: TicketStatus
  approval_request: RefundRequest | null
  approval_decision: { approved: boolean; note: string; reviewer: string; decided_at: string } | null
  created_at: string
  customer_name: string
}

export type Customer = {
  public_id: string
  full_name: string
  phone: string
  email: string | null
  created_at: string
}

/** Django Ninja LimitOffsetPagination response. */
export type Page<T> = { items: T[]; count: number }
