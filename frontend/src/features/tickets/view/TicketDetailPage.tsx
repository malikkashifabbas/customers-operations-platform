import { ArrowLeft, Bot, Radio } from 'lucide-react'
import Markdown from 'react-markdown'
import { Link, useParams } from 'react-router'

import { friendlyMessage } from '@/shared/api/errors'
import { cn } from '@/shared/lib/cn'
import { formatDateTime } from '@/shared/lib/format'
import { Card, ErrorState, PageSpinner } from '@/shared/ui'

import { useTicket, useTicketStream } from '../controller/useTickets'
import type { TimelineEntry } from '../model/types'
import { TicketStatusBadge } from './TicketStatusBadge'

const DOT: Record<TimelineEntry['kind'], string> = {
  status: 'bg-info-500',
  routing: 'bg-brand-500',
  tool: 'bg-ink-400',
  approval: 'bg-beacon-400',
  final: 'bg-success-500',
  error: 'bg-danger-500',
}

export default function TicketDetailPage() {
  const { ticketId = '' } = useParams()
  const ticket = useTicket(ticketId)
  const { timeline, live } = useTicketStream(ticket.data)

  if (ticket.isPending) return <PageSpinner />
  if (ticket.isError) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8">
        <ErrorState message={friendlyMessage(ticket.error)} onRetry={() => ticket.refetch()} />
      </div>
    )
  }

  const t = ticket.data
  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-8">
      <Link to="/tickets" className="inline-flex items-center gap-1.5 text-sm text-fg-muted hover:text-fg">
        <ArrowLeft className="size-4" />
        All tickets
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t.subject}</h1>
          <p className="mt-1 text-sm text-fg-muted">Opened {formatDateTime(t.created_at)}</p>
        </div>
        <div className="flex items-center gap-2">
          {live && (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-success-500">
              <Radio className="size-3.5 animate-pulse" /> Live
            </span>
          )}
          <TicketStatusBadge status={t.status} />
        </div>
      </div>

      <Card className="p-5">
        <p className="text-xs font-medium tracking-wide text-fg-muted uppercase">Your message</p>
        <p className="mt-2 text-sm whitespace-pre-wrap">{t.body}</p>
      </Card>

      {t.status === 'waiting_approval' && t.approval_request && (
        <div className="rounded-card border border-beacon-300 bg-beacon-50 p-4 text-sm dark:border-beacon-500/40 dark:bg-beacon-700/15">
          A refund of <strong>{t.approval_request.amount}</strong> for <strong>{t.approval_request.order_number}</strong> is waiting for a staff
          member. This page updates by itself when they decide.
        </div>
      )}

      {t.reply && (
        <Card className="p-5">
          <p className="flex items-center gap-1.5 text-xs font-medium tracking-wide text-fg-muted uppercase">
            <Bot className="size-3.5" /> Reply
          </p>
          <div className="prose-chat mt-2 text-sm">
            <Markdown>{t.reply}</Markdown>
          </div>
        </Card>
      )}

      {timeline.length > 0 && (
        <Card className="p-5">
          <p className="text-xs font-medium tracking-wide text-fg-muted uppercase">Progress</p>
          <ol className="mt-3 space-y-3 border-l border-line pl-4">
            {timeline.map((entry) => (
              <li key={entry.id} className="relative text-sm">
                <span className={cn('absolute top-1.5 -left-[21px] size-2.5 rounded-full ring-4 ring-surface', DOT[entry.kind])} />
                {entry.text}
              </li>
            ))}
          </ol>
        </Card>
      )}
    </div>
  )
}
