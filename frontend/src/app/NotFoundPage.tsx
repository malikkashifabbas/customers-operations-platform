import { Compass } from 'lucide-react'
import { Link } from 'react-router'

import { EmptyState } from '@/shared/ui'

export default function NotFoundPage() {
  return (
    <div className="grid min-h-full place-items-center">
      <EmptyState
        icon={<Compass className="size-6" />}
        title="Page not found"
        description="This page does not exist or has moved."
        action={
          <Link to="/" className="text-sm font-medium text-primary">
            Back to start
          </Link>
        }
      />
    </div>
  )
}
