import { useId, type InputHTMLAttributes, type ReactNode, type Ref, type TextareaHTMLAttributes } from 'react'

import { cn } from '@/shared/lib/cn'

const CONTROL =
  'w-full rounded-xl border border-line bg-surface px-3.5 text-sm text-fg placeholder:text-fg-muted/70 transition-colors focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30 aria-invalid:border-danger-500'

type FieldShellProps = { label: string; error?: string; hint?: ReactNode; children: (id: string, describedBy: string | undefined) => ReactNode }

function FieldShell({ label, error, hint, children }: FieldShellProps) {
  const id = useId()
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-fg">
        {label}
      </label>
      {children(id, describedBy)}
      {error ? (
        <p id={`${id}-error`} className="text-xs text-danger-500">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${id}-hint`} className="text-xs text-fg-muted">
            {hint}
          </p>
        )
      )}
    </div>
  )
}

type InputProps = InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: ReactNode }

export function TextField({ label, error, hint, className, ref, ...rest }: InputProps & { ref?: Ref<HTMLInputElement> }) {
  return (
    <FieldShell label={label} error={error} hint={hint}>
      {(id, describedBy) => (
        <input id={id} ref={ref} aria-invalid={!!error} aria-describedby={describedBy} className={cn(CONTROL, 'h-11', className)} {...rest} />
      )}
    </FieldShell>
  )
}

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; error?: string; hint?: ReactNode }

export function TextAreaField({ label, error, hint, className, ref, ...rest }: TextareaProps & { ref?: Ref<HTMLTextAreaElement> }) {
  return (
    <FieldShell label={label} error={error} hint={hint}>
      {(id, describedBy) => (
        <textarea id={id} ref={ref} aria-invalid={!!error} aria-describedby={describedBy} className={cn(CONTROL, 'min-h-28 py-2.5', className)} {...rest} />
      )}
    </FieldShell>
  )
}
