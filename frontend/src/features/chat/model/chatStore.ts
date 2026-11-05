import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

import { useAuthStore } from '@/features/auth/model/authStore'

import type { ChatMessage, Conversation, PendingAction } from './types'

const MAX_CONVERSATIONS = 30
const MAX_MESSAGES = 100

type ChatState = {
  conversations: Record<string, Conversation>
  ensure: (id: string) => void
  addMessage: (id: string, message: ChatMessage) => void
  patchMessage: (id: string, messageId: string, patch: (message: ChatMessage) => Partial<ChatMessage>) => void
  setPending: (id: string, pending: PendingAction | null) => void
  remove: (id: string) => void
  clearAll: () => void
}

function emptyConversation(id: string): Conversation {
  return { id, title: 'New chat', updatedAt: Date.now(), messages: [], pending: null }
}

function updateConversation(state: ChatState, id: string, update: (c: Conversation) => Partial<Conversation>) {
  const current = state.conversations[id] ?? emptyConversation(id)
  return { conversations: { ...state.conversations, [id]: { ...current, ...update(current), updatedAt: Date.now() } } }
}

/** The backend keeps chat memory (Redis, 24 h) but has no history endpoint, so the browser keeps what it showed. */
export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      conversations: {},
      ensure: (id) => set((s) => (s.conversations[id] ? s : updateConversation(s, id, () => ({})))),
      addMessage: (id, message) =>
        set((s) =>
          updateConversation(s, id, (c) => ({
            messages: [...c.messages, message].slice(-MAX_MESSAGES),
            title: c.messages.length === 0 && message.role === 'user' ? message.text.slice(0, 60) : c.title,
          })),
        ),
      patchMessage: (id, messageId, patch) =>
        set((s) => updateConversation(s, id, (c) => ({ messages: c.messages.map((m) => (m.id === messageId ? { ...m, ...patch(m) } : m)) }))),
      setPending: (id, pending) => set((s) => updateConversation(s, id, () => ({ pending }))),
      remove: (id) =>
        set((s) => {
          const rest = { ...s.conversations }
          delete rest[id]
          return { conversations: rest }
        }),
      clearAll: () => set({ conversations: {} }),
    }),
    {
      name: 'opspilot-chats',
      storage: createJSONStorage(() => localStorage),
      // Oldest chats drop off, so localStorage never fills up.
      partialize: (s) => ({
        conversations: Object.fromEntries(
          Object.values(s.conversations)
            .sort((a, b) => b.updatedAt - a.updatedAt)
            .slice(0, MAX_CONVERSATIONS)
            .map((c) => [c.id, c]),
        ),
      }),
    },
  ),
)

// Chats belong to one customer: signing out (or a dead session) wipes them from this browser.
useAuthStore.subscribe((state, previous) => {
  if (previous.refreshToken && !state.refreshToken) useChatStore.getState().clearAll()
})
