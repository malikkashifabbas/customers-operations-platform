import type { ReactNode } from 'react'

export function EmptyState({ icon, title, description, action }: { icon?: ReactNode; title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      {icon && <div className="mb-4 grid size-12 place-items-center rounded-2xl bg-brand-50 text-primary dark:bg-brand-950">{icon}</div>}
      <h3 className="text-base font-semibold text-fg">{title}</h3>
      {description && <p className="mt-1 max-w-sm text-sm text-fg-muted">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-card border border-danger-500/30 bg-danger-100 px-4 py-3 text-sm text-danger-500 dark:bg-danger-500/10">
      {message}
      {onRetry && (
        <button type="button" onClick={onRetry} className="ml-2 font-medium underline underline-offset-2">
          Try again
        </button>
      )}
    </div>
  )
}
