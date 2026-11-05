import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'

import { friendlyMessage } from '@/shared/api/errors'
import { config } from '@/shared/config'

import { authApi, authKeys } from '../model/authApi'
import { useAuthStore } from '../model/authStore'
import type { ChangePasswordValues, CustomerLoginValues, SignupValues, StaffLoginValues } from '../model/schemas'
import type { TenantPublic } from '../model/types'

export function useTenant(slug: string) {
  return useQuery({ queryKey: authKeys.tenant(slug), queryFn: () => authApi.getTenant(slug), staleTime: Infinity, retry: false })
}

export function useMe() {
  const signedIn = useAuthStore((s) => !!s.refreshToken)
  return useQuery({ queryKey: authKeys.me, queryFn: authApi.me, enabled: signedIn, staleTime: 5 * 60_000 })
}

export function useCustomerLogin(tenant: TenantPublic | undefined) {
  const setSession = useAuthStore((s) => s.setSession)
  const navigate = useNavigate()
  return useMutation({
    mutationFn: (values: CustomerLoginValues) => {
      if (!tenant) throw new Error('Unknown company')
      return authApi.customerLogin({ tenant_public_id: tenant.public_id, ...values })
    },
    onSuccess: (tokens) => {
      setSession(tokens, 'customer', tenant?.slug ?? null)
      navigate('/chat', { replace: true })
    },
  })
}

export function useSignup(tenant: TenantPublic | undefined) {
  const setSession = useAuthStore((s) => s.setSession)
  const navigate = useNavigate()
  return useMutation({
    mutationFn: ({ email, ...values }: SignupValues) => {
      if (!tenant) throw new Error('Unknown company')
      return authApi.customerSignup({ tenant_public_id: tenant.public_id, email: email || null, ...values })
    },
    onSuccess: (tokens) => {
      setSession(tokens, 'customer', tenant?.slug ?? null)
      toast.success('Welcome! Your account is ready.')
      navigate('/chat', { replace: true })
    },
  })
}

export function useStaffLogin() {
  const setSession = useAuthStore((s) => s.setSession)
  const navigate = useNavigate()
  return useMutation({
    mutationFn: (values: StaffLoginValues) => authApi.staffLogin(values),
    onSuccess: (tokens) => {
      setSession(tokens, 'staff', null)
      navigate('/staff/approvals', { replace: true })
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  return useMutation({
    mutationFn: async () => {
      const { refreshToken } = useAuthStore.getState()
      // Revoking on the server is best effort: the local session ends either way.
      await authApi.logout(refreshToken).catch(() => undefined)
    },
    onSettled: () => {
      const { role, tenantSlug, clear } = useAuthStore.getState()
      clear()
      queryClient.clear()
      navigate(role === 'staff' ? '/staff/login' : `/${tenantSlug ?? config.defaultTenant}/login`, { replace: true })
    },
  })
}

export function useChangePassword() {
  const setSession = useAuthStore((s) => s.setSession)
  return useMutation({
    mutationFn: ({ current_password, new_password }: ChangePasswordValues) => authApi.changePassword({ current_password, new_password }),
    onSuccess: (tokens) => {
      // The old tokens stopped working on the server (password fingerprint), so keep the new pair.
      const { role, tenantSlug } = useAuthStore.getState()
      if (role) setSession(tokens, role, tenantSlug)
      toast.success('Password changed. Other devices have been signed out.')
    },
    onError: (error) => toast.error(friendlyMessage(error)),
  })
}
