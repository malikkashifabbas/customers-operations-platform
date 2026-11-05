import { http } from '@/shared/api/http'

import type { AccessToken, Me, TenantPublic, Tokens } from './types'

export const authApi = {
  getTenant: (slug: string) => http.get<TenantPublic>(`/tenants/${encodeURIComponent(slug)}`, { auth: false }),

  customerLogin: (body: { tenant_public_id: string; phone: string; password: string }) =>
    http.post<Tokens>('/auth/customer/login', body, { auth: false }),

  customerSignup: (body: { tenant_public_id: string; full_name: string; phone: string; email: string | null; password: string }) =>
    http.post<Tokens>('/auth/customer/signup', body, { auth: false }),

  staffLogin: (body: { username: string; password: string }) => http.post<Tokens>('/auth/staff/login', body, { auth: false }),

  refresh: (refreshToken: string) => http.post<AccessToken>('/auth/refresh', { refresh_token: refreshToken }, { auth: false }),

  logout: (refreshToken: string | null) => http.post<void>('/auth/logout', { refresh_token: refreshToken }),

  me: () => http.get<Me>('/auth/me'),

  changePassword: (body: { current_password: string; new_password: string }) => http.post<Tokens>('/auth/password', body),
}

export const authKeys = {
  me: ['auth', 'me'] as const,
  tenant: (slug: string) => ['auth', 'tenant', slug] as const,
}
