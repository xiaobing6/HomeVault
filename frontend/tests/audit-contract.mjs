import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const testDir = dirname(fileURLToPath(import.meta.url))
const root = resolve(testDir, '..')

function readSource(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const auditApi = readSource('src/api/audit.ts')
const routerSource = readSource('src/router/index.ts')
const appLayout = readSource('src/layouts/AppLayout.vue')

for (const exportedInterface of ['AuditLogEntry', 'AuditLogFilters', 'AuditLogListResponse']) {
  assert.match(
    auditApi,
    new RegExp(`export\\s+interface\\s+${exportedInterface}\\b`),
    `Audit API should export ${exportedInterface}`
  )
}

assert.ok(
  auditApi.includes("apiClient.get<AuditLogListResponse>('/audit/logs'"),
  'Audit list API should call GET /audit/logs with the list response type'
)
assert.ok(
  auditApi.includes('apiClient.get<AuditLogEntry>(`/audit/logs/${logId}`)'),
  'Audit detail API should call GET /audit/logs/${logId} with the entry type'
)

assert.doesNotMatch(routerSource, /admin\/logs|\/admin\/logs/, 'Router must not add visible admin logs UI')
assert.doesNotMatch(appLayout, /admin\/logs|\/admin\/logs/, 'Layout must not add visible admin logs UI')
