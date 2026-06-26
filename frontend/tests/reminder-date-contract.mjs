import assert from 'node:assert/strict'

import { createServer } from 'vite'

const server = await createServer({
  root: process.cwd(),
  logLevel: 'error',
  server: { middlewareMode: true },
  appType: 'custom'
})

try {
  const { formatReminderDate, normalizeReminderDate } = await server.ssrLoadModule(
    '/src/utils/reminderDates.ts'
  )

  assert.equal(normalizeReminderDate('2026-06-20T13:45:00'), '2026-06-20')
  assert.equal(normalizeReminderDate('2026-06-20'), '2026-06-20')
  assert.equal(normalizeReminderDate(''), null)
  assert.equal(normalizeReminderDate(null), null)

  assert.equal(formatReminderDate('2026-06-21'), '2026/6/21')
  assert.equal(formatReminderDate('2026-06-21T13:45:00'), '2026/6/21')
  assert.equal(formatReminderDate(null), '-')
} finally {
  await server.close()
}
