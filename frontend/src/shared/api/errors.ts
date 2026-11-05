/** Every failed API call becomes an ApiError, so views show one kind of error whatever the backend sent. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

type ErrorBody = { code?: string; message?: string; detail?: string | { msg?: string; loc?: (string | number)[] }[] }

const FRIENDLY: Record<string, string> = {
  CONVERSATION_BUSY: 'The assistant is still answering your last message.',
  CONFIRMATION_PENDING: 'Please confirm or cancel the pending action first.',
  NOTHING_TO_CONFIRM: 'There is nothing waiting for your confirmation.',
  ASSISTANT_UNAVAILABLE: 'The assistant is busy right now. Please try again in a minute.',
}

const BY_STATUS: Record<number, string> = {
  401: 'Your session has ended. Please log in again.',
  403: 'You do not have access to this.',
  404: 'Not found.',
  429: 'Too many requests. Please wait a moment.',
  503: 'The service is temporarily unavailable.',
}

export async function toApiError(response: Response): Promise<ApiError> {
  let body: ErrorBody = {}
  try {
    body = (await response.json()) as ErrorBody
  } catch {
    // Non-JSON error page (proxy or server crash): fall back to the status text.
  }
  // Django Ninja validation errors arrive as a list under "detail".
  const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).filter(Boolean).join(', ') : body.detail
  const code = body.code ?? `HTTP_${response.status}`
  const message = body.message ?? detail ?? response.statusText
  return new ApiError(response.status, code, message || 'Request failed')
}

export function friendlyMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return FRIENDLY[error.code] ?? (error.status >= 500 || !error.message ? BY_STATUS[error.status] : undefined) ?? error.message
  }
  if (error instanceof DOMException && error.name === 'AbortError') return 'Stopped.'
  if (error instanceof TypeError) return 'Cannot reach the server. Is the backend running?'
  return 'Something went wrong.'
}
