import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from '@/app/App'
import { queryClient } from '@/app/queryClient'
import { installAuth } from '@/features/auth/model/session'

import './styles/index.css'

installAuth(queryClient)

const root = document.getElementById('root')
if (!root) throw new Error('#root is missing in index.html')

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
