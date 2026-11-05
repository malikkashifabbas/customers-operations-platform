import { http } from '@/shared/api/http'

import type { Customer, Page, StaffTicket } from './types'

export const PAGE_SIZE = 20

export const staffApi = {
  waitingApprovals: () => http.get<StaffTicket[]>('/staff/tickets/'),
  decide: (id: string, body: { approved: boolean; note: string }) => http.post<StaffTicket>(`/staff/tickets/${id}/decision`, body),
  customers: (offset: number, limit = PAGE_SIZE) => http.get<Page<Customer>>(`/customers/?limit=${limit}&offset=${offset}`),
  createCustomer: (body: { full_name: string; phone: string; email: string | null; password: string | null }) => http.post<Customer>('/customers/', body),
  setCustomerPassword: (id: string, newPassword: string) => http.post<void>(`/customers/${id}/password`, { new_password: newPassword }),
}

export const staffKeys = {
  approvals: ['staff', 'approvals'] as const,
  customers: (offset: number) => ['staff', 'customers', offset] as const,
}
