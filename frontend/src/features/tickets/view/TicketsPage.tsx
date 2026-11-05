import { ChevronRight, LifeBuoy, Plus } from 'lucide-react'
import { Link } from 'react-router'

import { friendlyMessage } from '@/shared/api/errors'
import { formatRelative } from '@/shared/lib/format'
import { buttonStyles, Card, EmptyState, ErrorState, PageSpinner } from '@/shared/ui'

import { useTickets } from '../controller/useTickets'
import { TicketStatusBadge } from './TicketStatusBadge'

export default function TicketsPage() {
  const tickets = useTickets()

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Support tickets</h1>
          <p className="mt-1 text-sm text-fg-muted">The assistant answers each ticket in the background; refunds wait for staff approval.</p>
        </div>
        <Link to="/tickets/new" className={buttonStyles()}>
          <Plus className="size-4" />
          New ticket
        </Link>
      </div>

      {tickets.isPending && <PageSpinner />}
      {tickets.isError && <ErrorState message={friendlyMessage(tickets.error)} onRetry={() => tickets.refetch()} />}
      {tickets.data && (
        <Card className="overflow-hidden">
          {tickets.data.length === 0 ? (
            <EmptyState icon={<LifeBuoy className="size-6" />} title="No tickets yet" description="Open one here, or ask the assistant in chat to open it for you." />
          ) : (
            <ul className="divide-y divide-line">
              {tickets.data.map((ticket) => (
                <li key={ticket.public_id}>
                  <Link to={`/tickets/${ticket.public_id}`} className="flex items-center gap-4 px-5 py-4 transition-colors hover:bg-surface-2">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-fg">{ticket.subject}</p>
                      <p className="mt-0.5 text-xs text-fg-muted">{formatRelative(ticket.created_at)}</p>
                    </div>
                    <TicketStatusBadge status={ticket.status} />
                    <ChevronRight className="size-4 text-fg-muted" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
    </div>
  )
}
