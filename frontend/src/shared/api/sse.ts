import { createParser } from 'eventsource-parser'

import { toApiError } from './errors'
import { authorizedFetch, type RequestOptions } from './http'

export type SseHandler = (event: string, data: unknown, id: string | undefined) => void

type StreamOptions = Pick<RequestOptions, 'method' | 'body' | 'signal'> & {
  onEvent: SseHandler
  lastEventId?: string
}

/** SSE over fetch, because the browser's EventSource cannot POST or send an Authorization header. */
export async function streamSse(path: string, { method = 'POST', body, signal, onEvent, lastEventId }: StreamOptions) {
  const response = await authorizedFetch(path, {
    method,
    body,
    signal,
    headers: { Accept: 'text/event-stream', ...(lastEventId && { 'Last-Event-ID': lastEventId }) },
  })
  if (!response.ok || !response.body) throw await toApiError(response)

  const parser = createParser({
    onEvent: (message) => {
      let data: unknown
      try {
        data = message.data ? JSON.parse(message.data) : {}
      } catch {
        data = { text: message.data }
      }
      onEvent(message.event ?? 'message', data, message.id)
    },
  })

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      parser.feed(value)
    }
  } finally {
    reader.releaseLock()
  }
}
