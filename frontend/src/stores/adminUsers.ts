import { defineStore } from 'pinia'

import {
  createAdminUserApi,
  fetchAdminRolesApi,
  listAdminUsersApi,
  resetAdminUserPasswordApi,
  updateAdminUserApi,
  type AdminPasswordResetRequest,
  type AdminRole,
  type AdminUser,
  type AdminUserCreateRequest,
  type AdminUserFilters,
  type AdminUserUpdateRequest
} from '../api/admin'

interface AdminUsersState {
  users: AdminUser[]
  roles: AdminRole[]
  filters: AdminUserFilters
  total: number
  page: number
  pageSize: number
  loading: boolean
  saving: boolean
}

const defaultFilters = (): AdminUserFilters => ({
  page: 1,
  page_size: 20
})

const paginationFilterKeys = new Set<keyof AdminUserFilters>(['page', 'page_size'])

function hasNonPaginationFilter(filters: AdminUserFilters): boolean {
  return (Object.keys(filters) as (keyof AdminUserFilters)[]).some((key) => !paginationFilterKeys.has(key))
}

let loadUsersRequestId = 0
let loadRolesRequestId = 0

export const useAdminUsersStore = defineStore('adminUsers', {
  state: (): AdminUsersState => ({
    users: [],
    roles: [],
    filters: defaultFilters(),
    total: 0,
    page: 1,
    pageSize: 20,
    loading: false,
    saving: false
  }),
  actions: {
    async loadUsers(filters?: AdminUserFilters) {
      if (filters) {
        this.filters = {
          ...this.filters,
          ...filters,
          page: hasNonPaginationFilter(filters) ? 1 : filters.page ?? this.filters.page
        }
      }

      const requestId = ++loadUsersRequestId
      this.loading = true
      try {
        const response = await listAdminUsersApi(this.filters)
        if (requestId !== loadUsersRequestId) return
        this.users = response.items
        this.total = response.total
        this.page = response.page
        this.pageSize = response.page_size
        this.filters = { ...this.filters, page: response.page, page_size: response.page_size }
      } catch (error) {
        if (requestId === loadUsersRequestId) throw error
      } finally {
        if (requestId === loadUsersRequestId) {
          this.loading = false
        }
      }
    },
    async loadRoles() {
      const requestId = ++loadRolesRequestId
      this.loading = true
      try {
        const roles = await fetchAdminRolesApi()
        if (requestId !== loadRolesRequestId) return
        this.roles = roles
      } catch (error) {
        if (requestId === loadRolesRequestId) throw error
      } finally {
        if (requestId === loadRolesRequestId) {
          this.loading = false
        }
      }
    },
    applyFilters(filters: AdminUserFilters) {
      this.filters = { ...this.filters, ...filters, page: 1 }
    },
    setPage(page: number) {
      this.filters = { ...this.filters, page }
      this.page = page
    },
    setPageSize(pageSize: number) {
      this.filters = { ...this.filters, page: 1, page_size: pageSize }
      this.page = 1
      this.pageSize = pageSize
    },
    resetFilters() {
      this.filters = defaultFilters()
      this.page = 1
      this.pageSize = this.filters.page_size ?? 20
    },
    async createUser(payload: AdminUserCreateRequest): Promise<AdminUser> {
      return await this.saveAndRefresh(() => createAdminUserApi(payload))
    },
    async updateUser(userId: number, payload: AdminUserUpdateRequest): Promise<AdminUser> {
      return await this.saveAndRefresh(() => updateAdminUserApi(userId, payload))
    },
    async resetPassword(userId: number, payload: AdminPasswordResetRequest): Promise<AdminUser> {
      return await this.saveAndRefresh(() => resetAdminUserPasswordApi(userId, payload))
    },
    async saveAndRefresh(operation: () => Promise<AdminUser>): Promise<AdminUser> {
      this.saving = true
      try {
        const result = await operation()
        try {
          await this.loadUsers()
        } catch {
          // A successful mutation should not be reported as failed because a follow-up refresh failed.
        }
        return result
      } finally {
        this.saving = false
      }
    }
  }
})
