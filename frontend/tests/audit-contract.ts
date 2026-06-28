import {
  getAuditLogApi,
  listAuditLogsApi,
  type AuditLogEntry,
  type AuditLogFilters,
  type AuditLogListResponse
} from '../src/api/audit'

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

void assertAuditApiContract
