import { config } from '@/shared/config'

import { toApiError } from './errors'

/** The auth feature plugs in here at startup, so shared/ never imports a feature (no circular imports). */
type AuthBridge = {
  getAccessToken: () => string | null
  refreshAccessToken: () => Promise<string | null>
  onSessionExpired: () => void
}

let bridge: AuthBridge = {
  getAccessToken: () => null,
  refreshAccessToken: async () => null,
  onSessionExpired: () => {},
}

export function configureAuth(next: AuthBridge) {
  bridge = next
}

// Several requests can hit 401 at once; they all wait for one refresh instead of each sending its own.
let refreshing: Promise<string | null> | null = null

function refreshOnce(): Promise<string | null> {
  refreshing ??= bridge.refreshAccessToken().finally(() => {
    refreshing = null
  })
  return refreshing
}

export type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  headers?: Record<string, string>
  signal?: AbortSignal
  auth?: boolean
}

/** fetch with the Bearer token; on 401 refreshes once and retries, so a 15-minute access token never logs anyone out mid-task. */
export async function authorizedFetch(path: string, options: RequestOptions = {}): Promise<Response> {
  const { method = 'GET', body, headers = {}, signal, auth = true } = options
  const send = (token: string | null) =>
    fetch(`${config.apiBase}${path}`, {
      method,
      signal,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined && { 'Content-Type': 'application/json' }),
        ...(token && { Authorization: `Bearer ${token}` }),
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    })

  let response = await send(auth ? bridge.getAccessToken() : null)
  if (response.status === 401 && auth) {
    const token = await refreshOnce()
    if (token) response = await send(token)
    if (!token || response.status === 401) bridge.onSessionExpired()
  }
  return response
}

export async function request<T>(path: string, options?: RequestOptions): Promise<T> {
  const response = await authorizedFetch(path, options)
  if (!response.ok) throw await toApiError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const http = {
  get: <T>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) => request<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'POST', body }),
}
