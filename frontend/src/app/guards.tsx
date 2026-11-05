import { Navigate, Outlet, useLocation } from 'react-router'

import { useAuthStore } from '@/features/auth/model/authStore'
import type { Role } from '@/features/auth/model/types'
import { config } from '@/shared/config'

/** Only a signed-in user of this role gets through; the server checks the token again on every request anyway. */
export function RequireRole({ role }: { role: Role }) {
  const signedIn = useAuthStore((s) => !!s.refreshToken)
  const currentRole = useAuthStore((s) => s.role)
  const tenantSlug = useAuthStore((s) => s.tenantSlug)
  const location = useLocation()
  if (signedIn && currentRole === role) return <Outlet />
  const loginPath = role === 'staff' ? '/staff/login' : `/${tenantSlug ?? config.defaultTenant}/login`
  return <Navigate to={loginPath} replace state={{ from: location.pathname }} />
}

/** Signed-in users skip the login pages. */
export function RedirectIfSignedIn() {
  const role = useAuthStore((s) => (s.refreshToken ? s.role : null))
  if (role === 'customer') return <Navigate to="/chat" replace />
  if (role === 'staff') return <Navigate to="/staff/approvals" replace />
  return <Outlet />
}
