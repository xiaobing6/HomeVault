import {
  getAuditLogApi,
  listAuditLogsApi,
  type AuditLogEntry,
  type AuditLogFilters,
  type AuditLogListResponse
} from '../src/api/audit'
import AuditLogsPage from '../src/pages/AuditLogsPage.vue'
import { router } from '../src/router'
import { useAuditLogsStore } from '../src/stores/auditLogs'

function expectType<T>(_value: T): void {}

const filters: AuditLogFilters = {
  action: 'item.create',
  resource_type: 'item',
  result: 'success',
  actor_user_id: 1,
  search: 'chair',
  occurred_from: '2026-01-01T00:00:00Z',
  occurred_to: '2026-01-31T23:59:59Z',
  page: 1,
  page_size: 20
}

async function assertAuditApiContract() {
  expectType<AuditLogListResponse>(await listAuditLogsApi(filters))
  expectType<AuditLogEntry>(await getAuditLogApi(1))
}

async function assertAuditUiContract() {
  expectType<typeof AuditLogsPage>(AuditLogsPage)
  expectType<boolean>(router.getRoutes().some((route) => route.name === 'audit-logs'))

  const auditLogs = useAuditLogsStore()
  auditLogs.applyFilters({ action: 'auth.login', result: 'failure' })
  auditLogs.setPage(2)
  auditLogs.setPageSize(40)
  auditLogs.resetFilters()
  await auditLogs.loadLogs(filters)
  expectType<boolean>(await auditLogs.openDetail(1))
  auditLogs.closeDetail()

  expectType<AuditLogEntry[]>(auditLogs.logs)
  expectType<AuditLogEntry | null>(auditLogs.selectedLog)
  expectType<AuditLogFilters>(auditLogs.filters)
  expectType<number>(auditLogs.total)
  expectType<number>(auditLogs.page)
  expectType<number>(auditLogs.pageSize)
  expectType<boolean>(auditLogs.loading)
}

void assertAuditApiContract
void assertAuditUiContract
