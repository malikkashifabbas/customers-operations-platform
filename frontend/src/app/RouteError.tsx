import { TriangleAlert } from 'lucide-react'
import { isRouteErrorResponse, useRouteError } from 'react-router'

import { Button, EmptyState } from '@/shared/ui'

/** Shown instead of a blank screen when a page crashes; the error stays in the console for debugging. */
export function RouteError() {
  const error = useRouteError()
  const message = isRouteErrorResponse(error) ? `${error.status} ${error.statusText}` : error instanceof Error ? error.message : 'Unknown error'

  return (
    <div className="grid min-h-full place-items-center px-4">
      <EmptyState
        icon={<TriangleAlert className="size-6" />}
        title="Something went wrong on this page"
        description={message}
        action={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => window.location.reload()}>
              Reload
            </Button>
            <Button onClick={() => window.location.assign('/')}>Go to start</Button>
          </div>
        }
      />
    </div>
  )
}
