import { SendHorizontal } from 'lucide-react'
import { useState, type KeyboardEvent } from 'react'

import { Button } from '@/shared/ui'

import type { TicketStatus } from '../model/types'

const MAX_LENGTH = 5000

// Same rules as the API (409 otherwise): one agent run at a time, and nothing while staff decide.
const BLOCKED: Partial<Record<TicketStatus, string>> = {
  open: 'The assistant is answering. You can reply when it is done.',
  waiting_approval: 'A staff member is deciding. You can reply after their decision.',
}

type Props = { status: TicketStatus; sending: boolean; onSend: (body: string, done: () => void) => void }

export function TicketReplyBox({ status, sending, onSend }: Props) {
  const [text, setText] = useState('')
  const blocked = BLOCKED[status]
  const canSend = !blocked && !sending && text.trim().length > 0

  const submit = () => {
    if (canSend) onSend(text.trim(), () => setText(''))
  }

  // Ctrl/Cmd+Enter sends; a plain Enter is a new line, since ticket replies are often several lines.
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <form
      className="rounded-card border border-line bg-surface p-3 shadow-card focus-within:border-ring"
      onSubmit={(event) => {
        event.preventDefault()
        submit()
      }}
    >
      <label htmlFor="ticket-reply" className="sr-only">
        Reply to this ticket
      </label>
      <textarea
        id="ticket-reply"
        value={text}
        rows={3}
        maxLength={MAX_LENGTH}
        disabled={!!blocked}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder={blocked ?? 'Write a follow-up… (Ctrl+Enter to send)'}
        className="w-full resize-y bg-transparent px-1 py-1 text-sm text-fg placeholder:text-fg-muted focus:outline-none disabled:cursor-not-allowed"
      />
      <div className="flex items-center justify-between gap-3 pt-2">
        <span className="text-xs text-fg-muted">The assistant remembers everything earlier in this ticket.</span>
        <Button type="submit" size="sm" icon={<SendHorizontal className="size-4" />} loading={sending} disabled={!canSend}>
          Send
        </Button>
      </div>
    </form>
  )
}
