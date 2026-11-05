import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

import type { Role, Tokens } from './types'

type AuthState = {
  accessToken: string | null
  refreshToken: string | null
  role: Role | null
  tenantSlug: string | null
  setSession: (tokens: Tokens, role: Role, tenantSlug: string | null) => void
  setAccessToken: (token: string) => void
  clear: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      role: null,
      tenantSlug: null,
      setSession: (tokens, role, tenantSlug) =>
        set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token, role, tenantSlug }),
      setAccessToken: (accessToken) => set({ accessToken }),
      clear: () => set({ accessToken: null, refreshToken: null, role: null, tenantSlug: null }),
    }),
    {
      name: 'opspilot-auth',
      storage: createJSONStorage(() => localStorage),
      // The access token stays in memory only; after a reload one refresh call gets a new one.
      partialize: ({ refreshToken, role, tenantSlug }) => ({ refreshToken, role, tenantSlug }),
    },
  ),
)
