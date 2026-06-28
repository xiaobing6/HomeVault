import { defineStore } from 'pinia'

import {
  getAuditLogApi,
  listAuditLogsApi,
  type AuditLogEntry,
  type AuditLogFilters
} from '../api/audit'

interface AuditLogsState {
  logs: AuditLogEntry[]
  selectedLog: AuditLogEntry | null
  filters: AuditLogFilters
  total: number
  page: number
  pageSize: number
  listLoading: boolean
  detailLoading: boolean
}

interface LoadRequestTracker {
  loadLogsRequestId: number
  loadDetailRequestId: number
}

const defaultFilters = (): AuditLogFilters => ({
  page: 1,
  page_size: 20
})

const paginationFilterKeys = new Set<keyof AuditLogFilters>(['page', 'page_size'])
const loadRequestTrackers = new WeakMap<object, LoadRequestTracker>()

function hasNonPaginationFilter(filters: AuditLogFilters): boolean {
  return (Object.keys(filters) as (keyof AuditLogFilters)[]).some((key) => !paginationFilterKeys.has(key))
}

function getLoadRequestTracker(store: object): LoadRequestTracker {
  let tracker = loadRequestTrackers.get(store)
  if (!tracker) {
    tracker = {
      loadLogsRequestId: 0,
      loadDetailRequestId: 0
    }
    loadRequestTrackers.set(store, tracker)
  }
  return tracker
}

export const useAuditLogsStore = defineStore('auditLogs', {
  state: (): AuditLogsState => ({
    logs: [],
    selectedLog: null,
    filters: defaultFilters(),
    total: 0,
    page: 1,
    pageSize: 20,
    listLoading: false,
    detailLoading: false
  }),
  getters: {
    loading: (state) => state.listLoading || state.detailLoading
  },
  actions: {
    async loadLogs(filters?: AuditLogFilters) {
      if (filters) {
        this.filters = {
          ...this.filters,
          ...filters,
          page: hasNonPaginationFilter(filters) ? 1 : filters.page ?? this.filters.page
        }
      }

      const tracker = getLoadRequestTracker(this)
      const requestId = ++tracker.loadLogsRequestId
      this.listLoading = true
      try {
        const response = await listAuditLogsApi(this.filters)
        if (requestId !== tracker.loadLogsRequestId) return
        this.logs = response.items
        this.total = response.total
        this.page = response.page
        this.pageSize = response.page_size
        this.filters = { ...this.filters, page: response.page, page_size: response.page_size }
      } catch (error) {
        if (requestId === tracker.loadLogsRequestId) throw error
      } finally {
        if (requestId === tracker.loadLogsRequestId) {
          this.listLoading = false
        }
      }
    },
    async openDetail(logId: number): Promise<boolean> {
      const tracker = getLoadRequestTracker(this)
      const requestId = ++tracker.loadDetailRequestId
      this.detailLoading = true
      try {
        const detail = await getAuditLogApi(logId)
        if (requestId !== tracker.loadDetailRequestId) return false
        this.selectedLog = detail
        return true
      } catch (error) {
        if (requestId === tracker.loadDetailRequestId) throw error
        return false
      } finally {
        if (requestId === tracker.loadDetailRequestId) {
          this.detailLoading = false
        }
      }
    },
    closeDetail() {
      const tracker = getLoadRequestTracker(this)
      tracker.loadDetailRequestId += 1
      this.selectedLog = null
      this.detailLoading = false
    },
    applyFilters(filters: AuditLogFilters) {
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
    }
  }
})
