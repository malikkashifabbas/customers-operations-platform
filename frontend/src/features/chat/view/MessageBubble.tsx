import { AlertTriangle, Bot } from 'lucide-react'
import Markdown from 'react-markdown'

import { cn } from '@/shared/lib/cn'

import type { ChatMessage } from '../model/types'
import { RoutingChips } from './RoutingChips'

export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <p className="max-w-[85%] rounded-2xl rounded-br-md bg-bubble-user px-4 py-2.5 text-sm whitespace-pre-wrap text-on-bubble-user shadow-sm">{message.text}</p>
      </div>
    )
  }

  const failed = message.status === 'error'
  const thinking = message.status === 'streaming' && !message.text
  return (
    <div className="flex gap-3">
      <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-full bg-brand-800 text-beacon-300 dark:bg-brand-700">
        <Bot className="size-4.5" />
      </span>
      <div className="min-w-0 max-w-[85%] space-y-1.5">
        {message.meta && message.meta.routes.length > 0 && <RoutingChips routes={message.meta.routes} />}
        <div
          className={cn(
            'rounded-2xl rounded-tl-md border px-4 py-2.5 text-sm shadow-sm',
            failed ? 'border-danger-500/30 bg-danger-100 text-danger-500 dark:bg-danger-500/10' : 'border-line bg-bubble-bot text-fg',
          )}
        >
          {thinking ? (
            <span className="inline-flex gap-1 py-1" aria-label="Assistant is thinking">
              {[0, 150, 300].map((delay) => (
                <span key={delay} className="size-1.5 animate-bounce rounded-full bg-fg-muted" style={{ animationDelay: `${delay}ms` }} />
              ))}
            </span>
          ) : failed ? (
            <p className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              {message.text}
            </p>
          ) : (
            <div className="prose-chat break-words">
              <Markdown>{message.text}</Markdown>
              {message.status === 'streaming' && <span className="ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 animate-blink bg-primary" />}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
