import { ArrowLeft, Bot, Radio, UserRound } from 'lucide-react'
import Markdown from 'react-markdown'
import { Link, useParams } from 'react-router'

import { friendlyMessage } from '@/shared/api/errors'
import { cn } from '@/shared/lib/cn'
import { formatDateTime, formatRelative } from '@/shared/lib/format'
import { Card, ErrorState, PageSpinner } from '@/shared/ui'

import { useReplyToTicket, useTicket, useTicketStream } from '../controller/useTickets'
import type { TicketDetail, TicketMessage, TimelineEntry } from '../model/types'
import { TicketReplyBox } from './TicketReplyBox'
import { TicketStatusBadge } from './TicketStatusBadge'

const DOT: Record<TimelineEntry['kind'], string> = {
  status: 'bg-info-500',
  customer: 'bg-brand-500',
  routing: 'bg-brand-300',
  tool: 'bg-ink-400',
  approval: 'bg-beacon-400',
  final: 'bg-success-500',
  error: 'bg-danger-500',
}

export default function TicketDetailPage() {
  const { ticketId = '' } = useParams()
  const ticket = useTicket(ticketId)
  const { timeline, live } = useTicketStream(ticket.data)
  const reply = useReplyToTicket(ticketId)

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
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight break-words">{t.subject}</h1>
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

      <Conversation ticket={t} />

      {t.status === 'waiting_approval' && t.approval_request && (
        <div className="rounded-card border border-beacon-300 bg-beacon-50 p-4 text-sm dark:border-beacon-500/40 dark:bg-beacon-700/15">
          A refund of <strong>{t.approval_request.amount}</strong> for <strong>{t.approval_request.order_number}</strong> is waiting for a staff
          member. This page updates by itself when they decide.
        </div>
      )}

      <TicketReplyBox status={t.status} sending={reply.isPending} onSend={(body, done) => reply.mutate(body, { onSuccess: done })} />

      {timeline.length > 0 && (
        <details className="group rounded-card border border-line bg-surface p-5 shadow-card" open={live}>
          <summary className="cursor-pointer text-xs font-medium tracking-wide text-fg-muted uppercase select-none">Activity</summary>
          <ol className="mt-3 space-y-3 border-l border-line pl-4">
            {timeline.map((entry) => (
              <li key={entry.id} className="relative text-sm">
                <span className={cn('absolute top-1.5 -left-[21px] size-2.5 rounded-full ring-4 ring-surface', DOT[entry.kind])} />
                {entry.text}
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  )
}

function Conversation({ ticket }: { ticket: TicketDetail }) {
  const working = ticket.status === 'open'
  return (
    <Card className="space-y-4 p-5" aria-live="polite">
      {ticket.messages.map((message) => (
        <MessageRow key={message.public_id} message={message} />
      ))}
      {working && (
        <div className="flex items-center gap-2 pl-11 text-sm text-fg-muted">
          <span className="inline-flex gap-1" aria-hidden="true">
            {[0, 150, 300].map((delay) => (
              <span key={delay} className="size-1.5 animate-bounce rounded-full bg-fg-muted" style={{ animationDelay: `${delay}ms` }} />
            ))}
          </span>
          The assistant is working on your ticket…
        </div>
      )}
    </Card>
  )
}

function MessageRow({ message }: { message: TicketMessage }) {
  const mine = message.author === 'customer'
  return (
    <div className="flex gap-3">
      <span
        className={cn(
          'mt-0.5 grid size-8 shrink-0 place-items-center rounded-full',
          mine ? 'bg-surface-2 text-fg-muted' : 'bg-brand-800 text-beacon-300 dark:bg-brand-700',
        )}
      >
        {mine ? <UserRound className="size-4" /> : <Bot className="size-4.5" />}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-fg-muted">
          <span className="font-medium text-fg">{mine ? 'You' : 'Assistant'}</span> · {formatRelative(message.created_at)}
        </p>
        {mine ? (
          <p className="mt-1 text-sm whitespace-pre-wrap break-words">{message.body}</p>
        ) : (
          <div className="prose-chat mt-1 text-sm break-words">
            <Markdown>{message.body}</Markdown>
          </div>
        )}
      </div>
    </div>
  )
}
