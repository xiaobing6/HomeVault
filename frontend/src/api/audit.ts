import { apiClient } from './client'

export interface AuditLogEntry {
  id: number
  occurred_at: string
  actor_user_id: number | null
  actor_username: string | null
  action: string
  resource_type: string
  resource_id: string | null
  resource_label: string | null
  result: string
  metadata: Record<string, unknown> | null
}

export interface AuditLogListResponse {
  items: AuditLogEntry[]
  total: number
  page: number
  page_size: number
}

export interface AuditLogFilters {
  action?: string | null
  resource_type?: string | null
  result?: string | null
  actor_user_id?: number | null
  search?: string | null
  occurred_from?: string | null
  occurred_to?: string | null
  page?: number
  page_size?: number
}

export async function listAuditLogsApi(filters: AuditLogFilters = {}): Promise<AuditLogListResponse> {
  const response = await apiClient.get<AuditLogListResponse>('/audit/logs', { params: filters })
  return response.data
}

export async function getAuditLogApi(logId: number): Promise<AuditLogEntry> {
  const response = await apiClient.get<AuditLogEntry>(`/audit/logs/${logId}`)
  return response.data
}
