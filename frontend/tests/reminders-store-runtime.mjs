import assert from 'node:assert/strict'

import { createServer } from 'vite'

function buildReminder(id) {
  return {
    id,
    title: `Reminder ${id}`,
    description: '',
    source_type: 'manual',
    item_id: null,
    loan_id: null,
    due_date: null,
    remind_at: null,
    status: 'pending',
    priority: 'normal',
    due_state: 'none',
    days_until_due: null,
    created_by_user_id: null,
    completed_by_user_id: null,
    dismissed_by_user_id: null,
    completed_at: null,
    dismissed_at: null,
    archived_at: null,
    created_at: '2026-06-20T00:00:00Z',
    updated_at: '2026-06-20T00:00:00Z',
    item: null,
    loan: null
  }
}

function buildResponse(config, data) {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config
  }
}

const server = await createServer({
  root: process.cwd(),
  logLevel: 'error',
  server: { middlewareMode: true },
  appType: 'custom'
})

try {
  const { createPinia } = await server.ssrLoadModule('pinia')
  const { apiClient } = await server.ssrLoadModule('/src/api/client.ts')
  const { useReminderStore } = await server.ssrLoadModule('/src/stores/reminders.ts')

  const pinia = createPinia()

  let resolveFirstRequest
  const firstRequest = new Promise((resolve) => {
    resolveFirstRequest = () => resolve(buildResponse({}, buildReminder(1)))
  })

  apiClient.defaults.adapter = async (config) => {
    if (config.url === '/reminders/1') return await firstRequest
    if (config.url === '/reminders/2') return buildResponse(config, buildReminder(2))
    throw new Error(`Unexpected request: ${config.url}`)
  }

  const reminders = useReminderStore(pinia)
  const firstDetail = reminders.openDetail(1)
  const secondDetail = reminders.openDetail(2)

  await secondDetail
  assert.equal(reminders.selectedReminder?.id, 2)

  resolveFirstRequest()
  await firstDetail

  assert.equal(
    reminders.selectedReminder?.id,
    2,
    'late detail responses must not overwrite the latest selected reminder'
  )
} finally {
  await server.close()
}
