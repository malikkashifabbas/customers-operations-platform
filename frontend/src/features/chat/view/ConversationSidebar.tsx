import { CircleAlert, Plus, Trash2 } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import { cn } from '@/shared/lib/cn'
import { formatRelative, newId } from '@/shared/lib/format'
import { Button } from '@/shared/ui'

import { useConversations } from '../controller/useConversations'

export function ConversationSidebar({ activeId }: { activeId: string }) {
  const { conversations, remove } = useConversations()
  const navigate = useNavigate()

  const onDelete = (id: string) => {
    remove(id)
    if (id === activeId) navigate(`/chat/${newId('c')}`, { replace: true })
  }

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-line bg-surface md:flex" aria-label="Conversations">
      <div className="p-3">
        <Button className="w-full" icon={<Plus className="size-4" />} onClick={() => navigate(`/chat/${newId('c')}`)}>
          New chat
        </Button>
      </div>
      <nav className="flex-1 overflow-y-auto px-2 pb-3">
        {conversations.length === 0 && <p className="px-3 py-2 text-xs text-fg-muted">Your chats will show up here.</p>}
        <ul className="space-y-0.5">
          {conversations.map((c) => (
            <li key={c.id} className="group relative">
              <Link
                to={`/chat/${c.id}`}
                aria-current={c.id === activeId ? 'page' : undefined}
                className={cn(
                  'block rounded-lg px-3 py-2 pr-9 text-sm transition-colors',
                  c.id === activeId ? 'bg-brand-50 text-brand-800 dark:bg-brand-950 dark:text-brand-200' : 'text-fg hover:bg-surface-2',
                )}
              >
                <span className="flex items-center gap-1.5">
                  {c.hasPending && <CircleAlert className="size-3.5 shrink-0 text-beacon-500" aria-label="Waiting for confirmation" />}
                  <span className="truncate">{c.title}</span>
                </span>
                <span className="text-xs text-fg-muted">{formatRelative(c.updatedAt)}</span>
              </Link>
              <button
                type="button"
                onClick={() => onDelete(c.id)}
                className="absolute top-2 right-2 rounded-md p-1 text-fg-muted opacity-0 transition-opacity group-hover:opacity-100 hover:text-danger-500 focus-visible:opacity-100"
                aria-label={`Remove "${c.title}" from this browser`}
              >
                <Trash2 className="size-3.5" />
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  )
}
