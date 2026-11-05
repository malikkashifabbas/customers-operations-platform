export type ToolCall = { name: string; args: Record<string, unknown> }

/** What a write tool waits for; mirrors the interrupt() payloads of the backend tools. */
export type PendingAction =
  | { type: 'ticket_confirmation'; subject: string; body: string }
  | { type: 'name_change'; old_name: string; new_name: string }
  | { type: 'email_change'; old_email: string; new_email: string }
  | { type: 'order_cancel'; order_number: string; amount: string }

export type TurnMeta = {
  routes: string[]
  toolCalls: ToolCall[]
  blockedReason: string | null
  guardRewrites: number
  latencyMs?: number
  tokens?: number
  llmCalls?: number
}

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  text: string
  status: 'streaming' | 'done' | 'error'
  createdAt: number
  meta?: TurnMeta
}

export type Conversation = {
  id: string
  title: string
  updatedAt: number
  messages: ChatMessage[]
  pending: PendingAction | null
}

/** Response of POST /api/chat/confirm (and /messages). */
export type ChatOut = {
  conversation_id: string
  reply: string
  tool_calls: ToolCall[]
  llm_calls: number
  tokens: number
  latency_ms: number
  blocked_reason: string | null
  output_flags: string[]
  output_retries: number
  routes: string[]
  status: 'answered' | 'confirmation_required'
  pending_action: PendingAction | null
}

/** Events of POST /api/chat/messages/stream (apps/chat/services.py + agents/core/streaming.py). */
export type ChatStreamEvent =
  | { event: 'start'; data: { conversation_id: string } }
  | { event: 'routing'; data: { domains: string[] } }
  | { event: 'token'; data: { text: string } }
  | { event: 'reset'; data: Record<string, never> }
  | { event: 'replace'; data: { text: string } }
  | { event: 'guardrail'; data: { blocked_reason: string } }
  | { event: 'tool_call'; data: ToolCall }
  | { event: 'tool_result'; data: { name: string; content: string } }
  | { event: 'confirmation_required'; data: { pending_action: PendingAction; reply: string } }
  | { event: 'done'; data: { conversation_id: string; latency_ms: number } }
  | { event: 'error'; data: { code: string; message: string } }
