import { Check, Inbox, X } from 'lucide-react'
import { useState } from 'react'

import { friendlyMessage } from '@/shared/api/errors'
import { formatRelative } from '@/shared/lib/format'
import { Badge, Button, Card, EmptyState, ErrorState, PageSpinner } from '@/shared/ui'

import { useApprovals, useDecision } from '../controller/useStaff'
import type { StaffTicket } from '../model/types'

export default function ApprovalsPage() {
  const approvals = useApprovals()

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Refund approvals</h1>
        <p className="mt-1 text-sm text-fg-muted">The assistant never refunds on its own. Each request waits here; your decision resumes it through Kafka.</p>
      </div>

      {approvals.isPending && <PageSpinner />}
      {approvals.isError && <ErrorState message={friendlyMessage(approvals.error)} onRetry={() => approvals.refetch()} />}
      {approvals.data?.length === 0 && (
        <Card>
          <EmptyState icon={<Inbox className="size-6" />} title="Nothing to approve" description="New refund requests show up here automatically." />
        </Card>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {approvals.data?.map((ticket) => (
          <ApprovalCard key={ticket.public_id} ticket={ticket} />
        ))}
      </div>
    </div>
  )
}

function ApprovalCard({ ticket }: { ticket: StaffTicket }) {
  const decide = useDecision()
  const [note, setNote] = useState('')
  const request = ticket.approval_request
  const answer = (approved: boolean) => decide.mutate({ id: ticket.public_id, approved, note })

  return (
    <Card className="flex flex-col p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-medium">{ticket.subject}</p>
          <p className="text-xs text-fg-muted">
            {ticket.customer_name} · {formatRelative(ticket.created_at)}
          </p>
        </div>
        {request && <Badge tone="beacon">{request.amount}</Badge>}
      </div>
      {request && (
        <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
          <dt className="text-fg-muted">Order</dt>
          <dd className="font-mono">{request.order_number}</dd>
          <dt className="text-fg-muted">Reason</dt>
          <dd>{request.reason}</dd>
        </dl>
      )}
      <p className="mt-3 line-clamp-3 text-sm text-fg-muted">{ticket.body}</p>
      <label className="mt-4 block text-sm">
        <span className="sr-only">Note for the customer</span>
        <input
          value={note}
          onChange={(event) => setNote(event.target.value)}
          maxLength={500}
          placeholder="Note (optional, shown to the customer)"
          className="h-9 w-full rounded-lg border border-line bg-surface px-3 text-sm focus:border-ring focus:outline-none"
        />
      </label>
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" size="sm" icon={<X className="size-4" />} disabled={decide.isPending} onClick={() => answer(false)}>
          Decline
        </Button>
        <Button size="sm" icon={<Check className="size-4" />} loading={decide.isPending} onClick={() => answer(true)}>
          Approve refund
        </Button>
      </div>
    </Card>
  )
}
