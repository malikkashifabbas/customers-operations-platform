import { BookOpen, CreditCard, LifeBuoy, UserRound, type LucideIcon } from 'lucide-react'

import { Badge, type BadgeTone } from '@/shared/ui'

const DOMAINS: Record<string, { label: string; icon: LucideIcon; tone: BadgeTone }> = {
  billing: { label: 'Billing', icon: CreditCard, tone: 'brand' },
  account: { label: 'Account', icon: UserRound, tone: 'info' },
  tickets: { label: 'Tickets', icon: LifeBuoy, tone: 'beacon' },
  knowledge: { label: 'Policies', icon: BookOpen, tone: 'success' },
}

/** Which specialists answered: the multi-agent routing made visible. */
export function RoutingChips({ routes }: { routes: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5" aria-label="Specialists that answered">
      {routes.map((route) => {
        const domain = DOMAINS[route] ?? { label: route, icon: BookOpen, tone: 'neutral' as const }
        const Icon = domain.icon
        return (
          <Badge key={route} tone={domain.tone} icon={<Icon className="size-3" />}>
            {domain.label}
          </Badge>
        )
      })}
    </div>
  )
}
