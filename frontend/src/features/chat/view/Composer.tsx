import { SendHorizontal, Square } from 'lucide-react'
import { useState, type KeyboardEvent } from 'react'

import { Button } from '@/shared/ui'

const MAX_LENGTH = 4000

type ComposerProps = { disabled: boolean; streaming: boolean; onSend: (text: string) => void; onStop: () => void }

export function Composer({ disabled, streaming, onSend, onStop }: ComposerProps) {
  const [text, setText] = useState('')
  const canSend = text.trim().length > 0 && !disabled && !streaming

  const submit = () => {
    if (!canSend) return
    onSend(text)
    setText('')
  }

  // Enter sends, Shift+Enter makes a new line; IME composition (Urdu keyboards) must not send half a word.
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <form
      className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-line bg-surface p-2 shadow-card focus-within:border-ring"
      onSubmit={(event) => {
        event.preventDefault()
        submit()
      }}
    >
      <label htmlFor="composer" className="sr-only">
        Message
      </label>
      <textarea
        id="composer"
        rows={1}
        value={text}
        maxLength={MAX_LENGTH}
        disabled={disabled}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder={disabled ? 'Confirm or cancel the action above first…' : 'Type your message…'}
        className="field-sizing-content max-h-40 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-sm text-fg placeholder:text-fg-muted focus:outline-none disabled:cursor-not-allowed"
      />
      {streaming ? (
        <Button variant="secondary" size="icon" onClick={onStop} aria-label="Stop the reply">
          <Square className="size-4 fill-current" />
        </Button>
      ) : (
        <Button type="submit" size="icon" disabled={!canSend} aria-label="Send message">
          <SendHorizontal className="size-4" />
        </Button>
      )}
    </form>
  )
}
