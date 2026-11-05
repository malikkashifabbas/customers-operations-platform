import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { friendlyMessage } from '@/shared/api/errors'

import type { NewCustomerValues } from '../model/schemas'
import { staffApi, staffKeys } from '../model/staffApi'
import type { StaffTicket } from '../model/types'

export function useApprovals() {
  // New refund requests arrive from the worker; polling keeps the queue fresh without a manual reload.
  return useQuery({ queryKey: staffKeys.approvals, queryFn: staffApi.waitingApprovals, refetchInterval: 10_000 })
}

export function useDecision() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, approved, note }: { id: string; approved: boolean; note: string }) => staffApi.decide(id, { approved, note }),
    // Optimistic: the card leaves the queue at once; it comes back if the server says no.
    onMutate: async ({ id }) => {
      await queryClient.cancelQueries({ queryKey: staffKeys.approvals })
      const previous = queryClient.getQueryData<StaffTicket[]>(staffKeys.approvals)
      queryClient.setQueryData<StaffTicket[]>(staffKeys.approvals, (items) => items?.filter((t) => t.public_id !== id))
      return { previous }
    },
    onError: (error, _vars, context) => {
      queryClient.setQueryData(staffKeys.approvals, context?.previous)
      toast.error(friendlyMessage(error))
    },
    onSuccess: (_ticket, { approved }) => toast.success(approved ? 'Refund approved. The assistant will finish the ticket.' : 'Refund declined.'),
    onSettled: () => queryClient.invalidateQueries({ queryKey: staffKeys.approvals }),
  })
}

export function useCustomers(offset: number) {
  return useQuery({ queryKey: staffKeys.customers(offset), queryFn: () => staffApi.customers(offset), placeholderData: keepPreviousData })
}

export function useCreateCustomer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ email, password, ...rest }: NewCustomerValues) => staffApi.createCustomer({ ...rest, email: email || null, password: password || null }),
    onSuccess: (customer) => {
      toast.success(`${customer.full_name} added.`)
      void queryClient.invalidateQueries({ queryKey: ['staff', 'customers'] })
    },
    onError: (error) => toast.error(friendlyMessage(error)),
  })
}

export function useSetCustomerPassword() {
  return useMutation({
    mutationFn: ({ id, password }: { id: string; password: string }) => staffApi.setCustomerPassword(id, password),
    onSuccess: () => toast.success('Password set. The customer can sign in with it now.'),
    onError: (error) => toast.error(friendlyMessage(error)),
  })
}
