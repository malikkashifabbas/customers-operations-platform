import { QueryClientProvider } from '@tanstack/react-query'
import { Suspense } from 'react'
import { RouterProvider } from 'react-router'
import { Toaster } from 'sonner'

import { PageSpinner } from '@/shared/ui'

import { queryClient } from './queryClient'
import { router } from './router'

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Suspense fallback={<PageSpinner />}>
        <RouterProvider router={router} />
      </Suspense>
      <Toaster position="top-right" richColors closeButton theme="system" />
    </QueryClientProvider>
  )
}
