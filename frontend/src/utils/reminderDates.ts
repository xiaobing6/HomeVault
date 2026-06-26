export function normalizeReminderDate(value?: string | null): string | null {
  const trimmed = value?.trim()
  if (!trimmed) return null
  return trimmed.slice(0, 10)
}

export function formatReminderDate(value?: string | null): string {
  const normalized = normalizeReminderDate(value)
  if (!normalized) return '-'

  const parts = normalized.split('-').map((part) => Number(part))
  if (parts.length !== 3 || parts.some((part) => !Number.isFinite(part))) {
    return value ?? '-'
  }

  const [year, month, day] = parts
  return `${year}/${month}/${day}`
}
