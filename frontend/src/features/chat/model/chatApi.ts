import { http } from '@/shared/api/http'
import { streamSse } from '@/shared/api/sse'

import type { ChatOut, ChatStreamEvent } from './types'

export const chatApi = {
  stream: (conversationId: string, message: string, signal: AbortSignal, onEvent: (event: ChatStreamEvent) => void) =>
    streamSse('/chat/messages/stream', {
      body: { conversation_id: conversationId, message },
      signal,
      onEvent: (event, data) => onEvent({ event, data } as ChatStreamEvent),
    }),

  confirm: (conversationId: string, approved: boolean) => http.post<ChatOut>('/chat/confirm', { conversation_id: conversationId, approved }),
}
