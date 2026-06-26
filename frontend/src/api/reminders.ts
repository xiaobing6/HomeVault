import { apiClient } from './client'

export type ReminderStatus = 'pending' | 'done' | 'dismissed'
export type ReminderSourceType = 'manual' | 'loan_return'
export type ReminderPriority = 'low' | 'normal' | 'high'
export type ReminderDueState = ReminderStatus | 'overdue' | 'upcoming' | 'scheduled' | 'none'
export type ReminderSort =
  | 'due_asc'
  | 'due_desc'
  | 'created_asc'
  | 'created_desc'
  | 'updated_asc'
  | 'updated_desc'
  | 'priority_desc'

export interface ReminderItemSummary {
  id: number
  name: string
  is_archived: boolean
}

export interface ReminderLoanSummary {
  id: number
  borrower_name: string
  expected_return_date: string | null
  returned_at: string | null
}

export interface ReminderSummary {
  id: number
  title: string
  description: string
  source_type: ReminderSourceType
  item_id: number | null
  loan_id: number | null
  due_date: string | null
  remind_at: string | null
  status: ReminderStatus
  priority: ReminderPriority
  due_state: ReminderDueState
  days_until_due: number | null
  created_by_user_id: number | null
  completed_by_user_id: number | null
  dismissed_by_user_id: number | null
  completed_at: string | null
  dismissed_at: string | null
  archived_at: string | null
  created_at: string
  updated_at: string
  item: ReminderItemSummary | null
  loan: ReminderLoanSummary | null
}

export interface ReminderDetail extends ReminderSummary {}

export interface ReminderListResponse {
  items: ReminderSummary[]
  total: number
  page: number
  page_size: number
}

export interface ReminderFilters {
  status?: ReminderStatus | null
  source_type?: ReminderSourceType | null
  item_id?: number | null
  loan_id?: number | null
  overdue?: boolean | null
  upcoming_days?: number | null
  include_archived?: boolean
  search?: string | null
  sort?: ReminderSort
  page?: number
  page_size?: number
}

export interface ReminderCreateRequest {
  title: string
  description?: string
  item_id?: number | null
  due_date?: string | null
  remind_at?: string | null
  priority?: ReminderPriority
}

export interface ReminderUpdateRequest {
  title?: string | null
  description?: string | null
  item_id?: number | null
  due_date?: string | null
  remind_at?: string | null
  priority?: ReminderPriority | null
}

export async function listRemindersApi(filters: ReminderFilters = {}): Promise<ReminderListResponse> {
  const response = await apiClient.get<ReminderListResponse>('/reminders', { params: filters })
  return response.data
}

export async function createReminderApi(payload: ReminderCreateRequest): Promise<ReminderDetail> {
  const response = await apiClient.post<ReminderDetail>('/reminders', payload)
  return response.data
}

export async function fetchReminderDetailApi(reminderId: number): Promise<ReminderDetail> {
  const response = await apiClient.get<ReminderDetail>(`/reminders/${reminderId}`)
  return response.data
}

export async function updateReminderApi(
  reminderId: number,
  payload: ReminderUpdateRequest
): Promise<ReminderDetail> {
  const response = await apiClient.patch<ReminderDetail>(`/reminders/${reminderId}`, payload)
  return response.data
}

export async function completeReminderApi(reminderId: number): Promise<ReminderDetail> {
  const response = await apiClient.post<ReminderDetail>(`/reminders/${reminderId}/complete`)
  return response.data
}

export async function dismissReminderApi(reminderId: number): Promise<ReminderDetail> {
  const response = await apiClient.post<ReminderDetail>(`/reminders/${reminderId}/dismiss`)
  return response.data
}

export async function reopenReminderApi(reminderId: number): Promise<ReminderDetail> {
  const response = await apiClient.post<ReminderDetail>(`/reminders/${reminderId}/reopen`)
  return response.data
}

export async function archiveReminderApi(reminderId: number): Promise<ReminderDetail> {
  const response = await apiClient.delete<ReminderDetail>(`/reminders/${reminderId}`)
  return response.data
}
