export const config = {
  apiBase: '/api',
  defaultTenant: import.meta.env.VITE_DEFAULT_TENANT ?? 'demo-company',
} as const
