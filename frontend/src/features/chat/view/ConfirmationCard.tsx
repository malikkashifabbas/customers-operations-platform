import { Ban, Check, LifeBuoy, Mail, PackageX, UserRound, X, type LucideIcon } from 'lucide-react'

import { Button } from '@/shared/ui'

import type { PendingAction } from '../model/types'

type Described = { icon: LucideIcon; title: string; rows: [string, string][]; danger?: boolean }

function describe(action: PendingAction): Described {
  switch (action.type) {
    case 'ticket_confirmation':
      return { icon: LifeBuoy, title: 'Open a support ticket', rows: [['Subject', action.subject], ['Details', action.body]] }
    case 'name_change':
      return { icon: UserRound, title: 'Change your name', rows: [['From', action.old_name], ['To', action.new_name]] }
    case 'email_change':
      return { icon: Mail, title: 'Change your email', rows: [['From', action.old_email], ['To', action.new_email], ['Note', 'A link goes to the new address; the email changes only when it is opened.']] }
    case 'order_cancel':
      return { icon: PackageX, title: 'Cancel an order', rows: [['Order', action.order_number], ['Amount', action.amount]], danger: true }
  }
}

/** The human-in-the-loop step: the agent paused (LangGraph interrupt) and only this answer lets the change happen. */
export function ConfirmationCard({ action, busy, onAnswer }: { action: PendingAction; busy: boolean; onAnswer: (approved: boolean) => void }) {
  const { icon: Icon, title, rows, danger } = describe(action)
  return (
    <section
      aria-label="Action waiting for your confirmation"
      className="mx-auto max-w-3xl rounded-2xl border border-beacon-300 bg-beacon-50 p-4 dark:border-beacon-500/40 dark:bg-beacon-700/15"
    >
      <div className="flex items-start gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-beacon-400 text-ink-950">
          <Icon className="size-4.5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-fg">{title}</p>
          <p className="text-xs text-fg-muted">Nothing has changed yet.</p>
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
            {rows.map(([label, value]) => (
              <div key={label} className="contents">
                <dt className="text-fg-muted">{label}</dt>
                <dd className="break-words text-fg">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" size="sm" icon={<X className="size-4" />} disabled={busy} onClick={() => onAnswer(false)}>
          Cancel
        </Button>
        <Button
          variant={danger ? 'danger' : 'primary'}
          size="sm"
          icon={danger ? <Ban className="size-4" /> : <Check className="size-4" />}
          loading={busy}
          onClick={() => onAnswer(true)}
        >
          Confirm
        </Button>
      </div>
    </section>
  )
}
