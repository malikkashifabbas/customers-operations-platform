import { CheckCircle2, Clock, Hourglass, XCircle } from 'lucide-react'

import { Badge, type BadgeTone } from '@/shared/ui'

import type { TicketStatus } from '../model/types'

const STATUS: Record<TicketStatus, { label: string; tone: BadgeTone; icon: typeof Clock }> = {
  open: { label: 'In progress', tone: 'info', icon: Clock },
  waiting_approval: { label: 'Waiting for staff', tone: 'beacon', icon: Hourglass },
  answered: { label: 'Answered', tone: 'success', icon: CheckCircle2 },
  failed: { label: 'Failed', tone: 'danger', icon: XCircle },
}

export function TicketStatusBadge({ status }: { status: TicketStatus }) {
  const { label, tone, icon: Icon } = STATUS[status]
  return (
    <Badge tone={tone} icon={<Icon className="size-3" />}>
      {label}
    </Badge>
  )
}
