import { Moon, Sun } from 'lucide-react'
import { useState } from 'react'

import { Button } from './Button'

const STORAGE_KEY = 'opspilot-theme'

function applyTheme(dark: boolean) {
  document.documentElement.classList.toggle('dark', dark)
  try {
    localStorage.setItem(STORAGE_KEY, dark ? 'dark' : 'light')
  } catch {
    // Private mode can block storage; the theme still applies for this visit.
  }
}

export function ThemeToggle() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))
  const toggle = () => {
    applyTheme(!dark)
    setDark(!dark)
  }
  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}>
      {dark ? <Sun className="size-4.5" /> : <Moon className="size-4.5" />}
    </Button>
  )
}
