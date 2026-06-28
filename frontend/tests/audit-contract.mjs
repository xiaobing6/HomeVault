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
const auditStore = readSource('src/stores/auditLogs.ts')
const auditPage = readSource('src/pages/AuditLogsPage.vue')

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

assert.match(routerSource, /path:\s*'admin\/logs'/, 'Router should define the admin logs child path')
assert.match(routerSource, /name:\s*'audit-logs'/, 'Audit logs route should use the audit-logs name')
assert.match(routerSource, /AuditLogsPage\.vue/, 'Audit logs route should lazy-load AuditLogsPage')
assert.match(routerSource, /permission:\s*'logs:view'/, 'Audit logs route should require logs:view')
assert.match(appLayout, /<PermissionGate\s+permission="logs:view">/, 'Layout should gate audit logs nav link')
assert.match(appLayout, /<el-menu-item\s+index="\/admin\/logs">/, 'Layout should link to /admin/logs')

assert.match(auditStore, /defineStore\(\s*'auditLogs'/, 'Audit logs store should use the auditLogs id')
assert.match(auditStore, /listAuditLogsApi/, 'Audit logs store should list logs through the API helper')
assert.match(auditStore, /getAuditLogApi/, 'Audit logs store should fetch detail through the API helper')
assert.match(auditStore, /selectedLog/, 'Audit logs store should keep selected detail state')
assert.match(auditStore, /async\s+loadLogs\(/, 'Audit logs store should expose loadLogs')
assert.match(auditStore, /async\s+openDetail\(/, 'Audit logs store should expose openDetail')
assert.match(auditStore, /closeDetail\(\)/, 'Audit logs store should expose closeDetail')
assert.match(auditStore, /hasNonPaginationFilter/, 'Audit logs store should reset pagination for non-page filters')

assert.match(auditPage, /useAuditLogsStore\(\)/, 'Audit logs page should use the audit logs store')
assert.match(auditPage, /onMounted\([\s\S]*auditLogs\.loadLogs\(\)/, 'Audit logs page should load logs on mount')
assert.match(auditPage, /v-model="searchValue"/, 'Audit logs page should expose a search filter')
assert.match(auditPage, /v-model="actionValue"/, 'Audit logs page should expose an action filter')
assert.match(auditPage, /v-model="resourceTypeValue"/, 'Audit logs page should expose a resource type filter')
assert.match(auditPage, /v-model="resultValue"/, 'Audit logs page should expose a result filter')
assert.match(auditPage, /@current-change="changePage"/, 'Audit logs page should support page changes')
assert.match(auditPage, /@size-change="changePageSize"/, 'Audit logs page should support page-size changes')
assert.match(auditPage, /openLogDetail\(row\.id\)/, 'Audit logs table should open detail by row id')
assert.match(
  auditPage,
  /const\s+detailLoaded\s*=\s*await\s+auditLogs\.openDetail\(logId\)[\s\S]*if\s*\(\s*!detailLoaded\s*\)\s*return[\s\S]*detailDialogOpen\.value\s*=\s*true/,
  'Audit logs page should only open the detail dialog when the current detail request is applied'
)
assert.match(auditPage, /const\s+detailDialogOpen\s*=\s*ref\(/, 'Audit detail should be shown in a dialog')
assert.match(auditPage, /<el-dialog[\s\S]*v-model="detailDialogOpen"/, 'Audit detail should use an Element Plus dialog')
assert.match(auditPage, /selectedLog/, 'Audit detail dialog should render the selected log')
assert.match(auditPage, /JSON\.stringify/, 'Audit detail dialog should render metadata as formatted JSON')
assert.match(auditPage, /async\s+function\s+refreshLogs\(\)/, 'Audit logs page should expose refreshLogs')
assert.match(
  auditPage,
  /async\s+function\s+refreshLogs\(\)[\s\S]*auditLogs\.loadLogs\(\)/,
  'Audit logs refresh should reload the current query without resetting filters'
)
assert.match(
  auditPage,
  /<el-button\s+:icon="Refresh"\s+@click="refreshLogs">/,
  'Audit logs header refresh button should refresh the current query'
)
assert.match(
  auditPage,
  /ElMessage\.error\(getChineseErrorMessage\(error\)\)/,
  'Audit logs page should surface API errors through Chinese error messages'
)
