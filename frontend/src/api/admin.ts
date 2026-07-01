import { apiClient } from './client'

export interface AdminPermission {
  code: string
  name: string
  description: string
}

export interface AdminRole {
  id: number
  code: string
  name: string
  description: string
  is_system: boolean
  is_active: boolean
  permissions: AdminPermission[]
}

export interface AdminUser {
  id: number
  username: string
  display_name: string
  is_active: boolean
  roles: string[]
  permissions: string[]
  created_at: string
  updated_at: string
}

export interface AdminUserListResponse {
  items: AdminUser[]
  total: number
  page: number
  page_size: number
}

export interface AdminUserFilters {
  search?: string | null
  role?: string | null
  is_active?: boolean | null
  page?: number
  page_size?: number
}

export interface AdminUserCreateRequest {
  username: string
  display_name: string
  password: string
  role_codes: string[]
}

export interface AdminUserUpdateRequest {
  display_name: string
  is_active: boolean
  role_codes: string[]
}

export interface AdminPasswordResetRequest {
  password: string
}

export interface AdminRoleCreateRequest {
  code: string
  name: string
  description: string
  permission_codes: string[]
  is_active: boolean
}

export interface AdminRoleUpdateRequest {
  name: string
  description: string
  permission_codes: string[]
  is_active: boolean
}

export async function listAdminUsersApi(filters: AdminUserFilters = {}): Promise<AdminUserListResponse> {
  const response = await apiClient.get<AdminUserListResponse>('/admin/users', { params: filters })
  return response.data
}

export async function fetchAdminRolesApi(): Promise<AdminRole[]> {
  const response = await apiClient.get<AdminRole[]>('/admin/roles')
  return response.data
}

export async function createAdminRoleApi(payload: AdminRoleCreateRequest): Promise<AdminRole> {
  const response = await apiClient.post<AdminRole>('/admin/roles', payload)
  return response.data
}

export async function updateAdminRoleApi(roleId: number, payload: AdminRoleUpdateRequest): Promise<AdminRole> {
  const response = await apiClient.patch<AdminRole>(`/admin/roles/${roleId}`, payload)
  return response.data
}

export async function createAdminUserApi(payload: AdminUserCreateRequest): Promise<AdminUser> {
  const response = await apiClient.post<AdminUser>('/admin/users', payload)
  return response.data
}

export async function updateAdminUserApi(userId: number, payload: AdminUserUpdateRequest): Promise<AdminUser> {
  const response = await apiClient.patch<AdminUser>(`/admin/users/${userId}`, payload)
  return response.data
}

export async function resetAdminUserPasswordApi(
  userId: number,
  payload: AdminPasswordResetRequest
): Promise<AdminUser> {
  const response = await apiClient.post<AdminUser>(`/admin/users/${userId}/reset-password`, payload)
  return response.data
}
