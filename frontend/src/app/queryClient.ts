import { QueryClient } from '@tanstack/react-query'

import { ApiError } from '@/shared/api/errors'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // Retrying a 4xx never helps (bad id, no access); only network and 5xx errors get a second try.
      retry: (count, error) => count < 2 && !(error instanceof ApiError && error.status < 500),
    },
    mutations: { retry: false },
  },
})
