import assert from 'node:assert/strict'

import { createServer } from 'vite'

function buildLog(id) {
  return {
    id,
    occurred_at: '2026-06-28T00:00:00Z',
    actor_user_id: 1,
    actor_username: 'admin',
    action: id === 1 ? 'auth.login' : 'config.residence.update',
    resource_type: id === 1 ? 'auth_session' : 'residence',
    resource_id: String(id),
    resource_label: `Resource ${id}`,
    result: 'success',
    metadata: { changed_fields: ['name'] }
  }
}

function buildList(page = 1) {
  return {
    items: [buildLog(page)],
    total: 1,
    page,
    page_size: 20
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

function deferredResponse(config, data) {
  let resolveResponse
  const promise = new Promise((resolve) => {
    resolveResponse = () => resolve(buildResponse(config, data))
  })
  return { promise, resolveResponse }
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
  const { useAuditLogsStore } = await server.ssrLoadModule('/src/stores/auditLogs.ts')

  const pinia = createPinia()
  const auditLogs = useAuditLogsStore(pinia)

  let requestedParams
  apiClient.defaults.adapter = async (config) => {
    if (config.url === '/audit/logs') {
      requestedParams = config.params
      return buildResponse(config, buildList(1))
    }
    throw new Error(`Unexpected request: ${config.url}`)
  }

  auditLogs.setPage(3)
  await auditLogs.loadLogs({ search: 'admin' })

  assert.equal(requestedParams.page, 1, 'non-pagination filters should reset audit logs to page 1')
  assert.equal(auditLogs.page, 1, 'store page should match the reset API response page')
  assert.equal(auditLogs.logs[0]?.id, 1)

  let firstDetail
  apiClient.defaults.adapter = async (config) => {
    if (config.url === '/audit/logs/1') {
      firstDetail = deferredResponse(config, buildLog(1))
      return await firstDetail.promise
    }
    if (config.url === '/audit/logs/2') return buildResponse(config, buildLog(2))
    throw new Error(`Unexpected request: ${config.url}`)
  }

  const firstOpen = auditLogs.openDetail(1)
  const secondOpen = auditLogs.openDetail(2)

  assert.equal(await secondOpen, true, 'latest audit detail request should report that it was applied')
  assert.equal(auditLogs.selectedLog?.id, 2)
  assert.equal(
    auditLogs.loading,
    false,
    'stale pending audit detail requests should not keep the store loading after the latest detail resolves'
  )

  firstDetail.resolveResponse()
  assert.equal(await firstOpen, false, 'stale audit detail request should report that it was ignored')

  assert.equal(
    auditLogs.selectedLog?.id,
    2,
    'late audit detail responses must not overwrite the latest selected log'
  )

  let thirdDetail
  apiClient.defaults.adapter = async (config) => {
    if (config.url === '/audit/logs/3') {
      thirdDetail = deferredResponse(config, buildLog(3))
      return await thirdDetail.promise
    }
    throw new Error(`Unexpected request: ${config.url}`)
  }

  const thirdOpen = auditLogs.openDetail(3)
  assert.equal(auditLogs.detailLoading, true, 'detail loading should be true while the current detail request is pending')

  auditLogs.closeDetail()
  assert.equal(auditLogs.selectedLog, null, 'closeDetail should clear selected detail')
  assert.equal(auditLogs.detailLoading, false, 'closeDetail should stop detail loading for invalidated requests')

  thirdDetail.resolveResponse()
  assert.equal(await thirdOpen, false, 'closing detail should invalidate the pending detail request')
  assert.equal(auditLogs.selectedLog, null, 'invalidated detail response should not repopulate selected detail')
} finally {
  await server.close()
}
