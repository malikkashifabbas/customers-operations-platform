import { LoaderCircle } from 'lucide-react'

import { cn } from '@/shared/lib/cn'

export function Spinner({ className, label = 'Loading' }: { className?: string; label?: string }) {
  return <LoaderCircle role="status" aria-label={label} className={cn('size-5 animate-spin text-fg-muted', className)} />
}

export function PageSpinner() {
  return (
    <div className="grid min-h-[50vh] place-items-center">
      <Spinner className="size-7 text-primary" />
    </div>
  )
}
