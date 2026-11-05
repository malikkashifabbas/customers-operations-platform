import { Bot, ShieldCheck, Sparkles } from 'lucide-react'
import type { ReactNode } from 'react'

import { Logo, ThemeToggle } from '@/shared/ui'

const POINTS = [
  { icon: ShieldCheck, text: 'Signed-in sessions: the assistant only ever sees your own data.' },
  { icon: Bot, text: 'Specialists for orders, account, tickets and policies work together.' },
  { icon: Sparkles, text: 'Nothing changes until you confirm it.' },
]

/** Split screen: brand panel on wide screens, form card everywhere. */
export function AuthShell({ title, subtitle, children, footer }: { title: string; subtitle?: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="grid min-h-full lg:grid-cols-[1.1fr_1fr]">
      <aside className="relative hidden overflow-hidden bg-brand-900 p-12 text-white lg:flex lg:flex-col lg:justify-between dark:bg-brand-950">
        <div className="absolute -top-24 -right-24 size-96 rounded-full bg-brand-600/40 blur-3xl" aria-hidden="true" />
        <div className="absolute -bottom-32 -left-16 size-80 rounded-full bg-beacon-500/25 blur-3xl" aria-hidden="true" />
        <Logo className="relative [&_span]:text-white" />
        <div className="relative max-w-md">
          <h2 className="text-3xl leading-tight font-semibold">Support that knows your account and keeps you in control.</h2>
          <ul className="mt-8 space-y-4">
            {POINTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex gap-3 text-brand-100">
                <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-white/10 text-beacon-300">
                  <Icon className="size-4" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-sm text-brand-200">OpsPilot · multi-agent customer support</p>
      </aside>

      <main className="flex flex-col px-4 py-6 sm:px-8">
        <div className="flex items-center justify-between">
          <Logo className="lg:invisible" />
          <ThemeToggle />
        </div>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-10">
          <h1 className="text-2xl font-semibold tracking-tight text-fg">{title}</h1>
          {subtitle && <p className="mt-1.5 text-sm text-fg-muted">{subtitle}</p>}
          <div className="mt-8">{children}</div>
          {footer && <div className="mt-6 text-center text-sm text-fg-muted">{footer}</div>}
        </div>
      </main>
    </div>
  )
}
