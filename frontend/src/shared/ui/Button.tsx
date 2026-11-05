import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { buttonStyles, type Size, type Variant } from './buttonStyles'
import { Spinner } from './Spinner'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: ReactNode
}

export function Button({ variant, size, loading = false, icon, className, children, disabled, type = 'button', ...rest }: ButtonProps) {
  return (
    <button type={type} disabled={disabled || loading} aria-busy={loading || undefined} className={buttonStyles({ variant, size, className })} {...rest}>
      {loading ? <Spinner className="size-4" /> : icon}
      {children}
    </button>
  )
}
