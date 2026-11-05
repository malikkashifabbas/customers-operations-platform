import { Navigate } from 'react-router'

import { useAuthStore } from '@/features/auth/model/authStore'
import { config } from '@/shared/config'

export function HomeRedirect() {
  const { role, tenantSlug } = useAuthStore.getState()
  if (role === 'staff') return <Navigate to="/staff/approvals" replace />
  if (role === 'customer') return <Navigate to="/chat" replace />
  return <Navigate to={`/${tenantSlug ?? config.defaultTenant}/login`} replace />
}
