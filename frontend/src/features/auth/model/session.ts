import type { QueryClient } from '@tanstack/react-query'

import { configureAuth } from '@/shared/api/http'

import { authApi } from './authApi'
import { useAuthStore } from './authStore'

/** Called once in main.tsx: lets the shared HTTP client read, refresh and drop the session. */
export function installAuth(queryClient: QueryClient) {
  configureAuth({
    getAccessToken: () => useAuthStore.getState().accessToken,
    refreshAccessToken: async () => {
      const { refreshToken, setAccessToken } = useAuthStore.getState()
      if (!refreshToken) return null
      try {
        const { access_token } = await authApi.refresh(refreshToken)
        setAccessToken(access_token)
        return access_token
      } catch {
        return null
      }
    },
    onSessionExpired: () => {
      useAuthStore.getState().clear()
      queryClient.clear()
    },
  })
}
