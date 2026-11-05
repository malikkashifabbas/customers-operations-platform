const dateTime = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })
const relative = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })

export function formatDateTime(value: string | number | Date) {
  return dateTime.format(new Date(value))
}

export function formatRelative(value: string | number | Date) {
  const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000)
  const steps: [Intl.RelativeTimeFormatUnit, number][] = [
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ]
  for (const [unit, size] of steps) {
    if (Math.abs(seconds) >= size) return relative.format(Math.round(seconds / size), unit)
  }
  return 'just now'
}

export function formatMs(ms: number) {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`
}

export function newId(prefix: string) {
  return `${prefix}-${crypto.randomUUID().replaceAll('-', '').slice(0, 12)}`
}
