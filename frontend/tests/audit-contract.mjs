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

assert.match(
  auditApi,
  /apiClient\s*\.\s*get\s*<\s*AuditLogListResponse\s*>\s*\(\s*['"]\/audit\/logs['"]/,
  'Audit list API should call GET /audit/logs with the list response type'
)
assert.match(
  auditApi,
  /apiClient\s*\.\s*get\s*<\s*AuditLogEntry\s*>\s*\(\s*`\/audit\/logs\/\$\{\s*logId\s*\}`/,
  'Audit detail API should call GET /audit/logs/${logId} with the entry type'
)

const forbiddenVisibleAuditUiPatterns = [
  { label: 'admin logs route or nav URL', pattern: /\/?admin\/logs\b/ },
  { label: 'audit logs route or nav URL', pattern: /\/?audit\/logs\b/ },
  { label: 'audit-logs route name or nav key', pattern: /\baudit-logs\b/ },
  { label: 'AuditLogs page or component', pattern: /\bAuditLogs[A-Za-z0-9_]*\b/ }
]

for (const { label, pattern } of forbiddenVisibleAuditUiPatterns) {
  assert.doesNotMatch(routerSource, pattern, `Router must not add visible audit log UI: ${label}`)
  assert.doesNotMatch(appLayout, pattern, `Layout must not add visible audit log UI: ${label}`)
}
