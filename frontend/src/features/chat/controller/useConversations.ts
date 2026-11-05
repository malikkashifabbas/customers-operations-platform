import { useChatStore } from '../model/chatStore'

export function useConversations() {
  // Select the stored object itself (stable reference); a selector that maps to new objects re-renders forever.
  const conversations = useChatStore((s) => s.conversations)
  const remove = useChatStore((s) => s.remove)
  const list = Object.values(conversations)
    .filter((c) => c.messages.length > 0)
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .map(({ id, title, updatedAt, pending }) => ({ id, title, updatedAt, hasPending: !!pending }))
  return { conversations: list, remove }
}
