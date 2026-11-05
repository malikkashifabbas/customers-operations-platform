import { PanelRightClose, PanelRightOpen } from 'lucide-react'
import { useState } from 'react'
import { Navigate, useParams } from 'react-router'

import { newId } from '@/shared/lib/format'
import { Button } from '@/shared/ui'

import { useChat } from '../controller/useChat'
import { Composer } from './Composer'
import { ConfirmationCard } from './ConfirmationCard'
import { ConversationSidebar } from './ConversationSidebar'
import { DebugPanel } from './DebugPanel'
import { MessageList } from './MessageList'

export default function ChatPage() {
  const { conversationId } = useParams()
  // Remount per conversation so streaming state never leaks from one chat into another.
  if (!conversationId) return <Navigate to={`/chat/${newId('c')}`} replace />
  return <ChatScreen key={conversationId} conversationId={conversationId} />
}

function ChatScreen({ conversationId }: { conversationId: string }) {
  const chat = useChat(conversationId)
  const [showDebug, setShowDebug] = useState(true)
  const lastReply = chat.messages.findLast((m) => m.role === 'assistant')

  return (
    <div className="flex h-full min-h-0">
      <ConversationSidebar activeId={conversationId} />

      <section className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <p className="truncate text-sm font-medium text-fg-muted">Support assistant</p>
          <Button
            variant="ghost"
            size="icon"
            className="hidden lg:inline-flex"
            onClick={() => setShowDebug((v) => !v)}
            aria-label={showDebug ? 'Hide agent details' : 'Show agent details'}
            aria-pressed={showDebug}
          >
            {showDebug ? <PanelRightClose className="size-4.5" /> : <PanelRightOpen className="size-4.5" />}
          </Button>
        </div>

        <MessageList messages={chat.messages} onSuggestion={chat.send} />

        <div className="space-y-3 border-t border-line bg-surface/60 px-4 py-3 backdrop-blur">
          {chat.pending && (
            <ConfirmationCard
              action={chat.pending}
              busy={chat.confirm.isPending}
              onAnswer={(approved) => chat.confirm.mutate(approved)}
            />
          )}
          <Composer disabled={!!chat.pending || chat.confirm.isPending} streaming={chat.streaming} onSend={chat.send} onStop={chat.stop} />
        </div>
      </section>

      {showDebug && <DebugPanel message={lastReply} />}
    </div>
  )
}
