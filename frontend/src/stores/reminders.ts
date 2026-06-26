import { defineStore } from 'pinia'

import {
  archiveReminderApi,
  completeReminderApi,
  createReminderApi,
  dismissReminderApi,
  fetchReminderDetailApi,
  listRemindersApi,
  reopenReminderApi,
  updateReminderApi,
  type ReminderCreateRequest,
  type ReminderDetail,
  type ReminderFilters,
  type ReminderSummary,
  type ReminderUpdateRequest
} from '../api/reminders'

interface RemindersState {
  reminders: ReminderSummary[]
  selectedReminder: ReminderDetail | null
  total: number
  page: number
  pageSize: number
  loading: boolean
  saving: boolean
  filters: ReminderFilters
}

const defaultFilters = (): ReminderFilters => ({
  page: 1,
  page_size: 20,
  sort: 'due_asc',
  include_archived: false
})

const paginationFilterKeys = new Set<keyof ReminderFilters>(['page', 'page_size'])

function hasNonPaginationFilter(filters: ReminderFilters): boolean {
  return (Object.keys(filters) as (keyof ReminderFilters)[]).some((key) => !paginationFilterKeys.has(key))
}

let loadRemindersRequestId = 0

export const useReminderStore = defineStore('reminders', {
  state: (): RemindersState => ({
    reminders: [],
    selectedReminder: null,
    total: 0,
    page: 1,
    pageSize: 20,
    loading: false,
    saving: false,
    filters: defaultFilters()
  }),
  actions: {
    async loadReminders(filters?: ReminderFilters) {
      if (filters) {
        this.filters = {
          ...this.filters,
          ...filters,
          page: hasNonPaginationFilter(filters) ? 1 : filters.page ?? this.filters.page
        }
      }

      const requestId = ++loadRemindersRequestId
      this.loading = true
      try {
        const response = await listRemindersApi(this.filters)
        if (requestId !== loadRemindersRequestId) return
        this.reminders = response.items
        this.total = response.total
        this.page = response.page
        this.pageSize = response.page_size
      } catch (error) {
        if (requestId === loadRemindersRequestId) throw error
      } finally {
        if (requestId === loadRemindersRequestId) {
          this.loading = false
        }
      }
    },
    async openDetail(reminderId: number) {
      this.loading = true
      try {
        this.selectedReminder = await fetchReminderDetailApi(reminderId)
      } finally {
        this.loading = false
      }
    },
    applyFilters(filters: ReminderFilters) {
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
    closeDetail() {
      this.selectedReminder = null
    },
    async createReminder(payload: ReminderCreateRequest): Promise<ReminderDetail> {
      return await this.saveAndRefresh(() => createReminderApi(payload))
    },
    async updateReminder(reminderId: number, payload: ReminderUpdateRequest): Promise<ReminderDetail> {
      return await this.saveAndRefresh(() => updateReminderApi(reminderId, payload))
    },
    async completeReminder(reminderId: number): Promise<ReminderDetail> {
      return await this.saveAndRefresh(() => completeReminderApi(reminderId))
    },
    async dismissReminder(reminderId: number): Promise<ReminderDetail> {
      return await this.saveAndRefresh(() => dismissReminderApi(reminderId))
    },
    async reopenReminder(reminderId: number): Promise<ReminderDetail> {
      return await this.saveAndRefresh(() => reopenReminderApi(reminderId))
    },
    async archiveReminder(reminderId: number): Promise<ReminderDetail> {
      return await this.saveAndRefresh(() => archiveReminderApi(reminderId))
    },
    async saveAndRefresh(operation: () => Promise<ReminderDetail>): Promise<ReminderDetail> {
      this.saving = true
      try {
        const result = await operation()
        this.selectedReminder = result
        try {
          await this.loadReminders()
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
