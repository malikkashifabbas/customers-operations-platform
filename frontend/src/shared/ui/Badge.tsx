import type { ReactNode } from 'react'

import { cn } from '@/shared/lib/cn'

const TONES = {
  neutral: 'bg-surface-2 text-fg-muted',
  brand: 'bg-brand-100 text-brand-800 dark:bg-brand-900 dark:text-brand-200',
  beacon: 'bg-beacon-100 text-beacon-700 dark:bg-beacon-700/30 dark:text-beacon-200',
  success: 'bg-success-100 text-success-500 dark:bg-success-500/15',
  warning: 'bg-warning-100 text-warning-500 dark:bg-warning-500/15',
  danger: 'bg-danger-100 text-danger-500 dark:bg-danger-500/15',
  info: 'bg-info-100 text-info-500 dark:bg-info-500/15',
} as const

export type BadgeTone = keyof typeof TONES

export function Badge({ tone = 'neutral', icon, children, className }: { tone?: BadgeTone; icon?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium', TONES[tone], className)}>
      {icon}
      {children}
    </span>
  )
}
