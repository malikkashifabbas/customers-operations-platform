import { cn } from '@/shared/lib/cn'

const VARIANTS = {
  primary: 'bg-primary text-on-primary hover:bg-primary-hover shadow-sm',
  accent: 'bg-accent text-on-accent hover:brightness-95 shadow-sm',
  secondary: 'bg-surface text-fg border border-line hover:bg-surface-2',
  ghost: 'text-fg-muted hover:bg-surface-2 hover:text-fg',
  danger: 'bg-danger-500 text-white hover:brightness-110 shadow-sm',
} as const

const SIZES = {
  sm: 'h-8 px-3 text-sm gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-12 px-5 text-base gap-2',
  icon: 'size-9 justify-center',
} as const

export type Variant = keyof typeof VARIANTS
export type Size = keyof typeof SIZES

/** Button look for other elements too (a router Link styled as a button), so links never wrap a <button>. */
export function buttonStyles({ variant = 'primary', size = 'md', className }: { variant?: Variant; size?: Size; className?: string } = {}) {
  return cn(
    'inline-flex shrink-0 items-center justify-center rounded-xl font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60',
    VARIANTS[variant],
    SIZES[size],
    className,
  )
}
