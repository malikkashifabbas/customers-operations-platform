import { cn } from '@/shared/lib/cn'

export function Logo({ className, withName = true }: { className?: string; withName?: boolean }) {
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <svg viewBox="0 0 32 32" className="size-8" aria-hidden="true">
        <rect width="32" height="32" rx="8" className="fill-brand-800 dark:fill-brand-600" />
        <path d="M7 19.5 25 9l-6.5 16-3.4-6.1L7 19.5Z" className="fill-beacon-400" />
        <path d="m15.1 18.9 3.4 6.1L25 9 15.1 18.9Z" className="fill-beacon-100" />
      </svg>
      {withName && (
        <span className="text-lg font-semibold tracking-tight text-fg">
          Ops<span className="text-primary">Pilot</span>
        </span>
      )}
    </span>
  )
}
