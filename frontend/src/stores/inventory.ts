import { defineStore } from 'pinia'

import {
  adjustQuantityApi,
  archiveItemApi,
  borrowItemApi,
  changeItemStatusApi,
  createItemApi,
  deleteAttachmentApi,
  deleteImageApi,
  fetchItemDetailApi,
  listItemsApi,
  moveItemApi,
  returnLoanApi,
  updateImageApi,
  updateItemApi,
  uploadAttachmentApi,
  uploadImageApi,
  type ArchiveItemRequest,
  type ChangeStatusRequest,
  type ItemCreateRequest,
  type ItemDetail,
  type ItemFilters,
  type ItemImageUpdateRequest,
  type ItemSummary,
  type ItemUpdateRequest,
  type LoanCreateRequest,
  type LoanReturnRequest,
  type MoveItemRequest,
  type QuantityAdjustmentRequest
} from '../api/inventory'

interface InventoryState {
  items: ItemSummary[]
  selectedItem: ItemDetail | null
  total: number
  page: number
  pageSize: number
  loading: boolean
  saving: boolean
  viewMode: 'cards' | 'table'
  filters: ItemFilters
}

const defaultFilters = (): ItemFilters => ({
  page: 1,
  page_size: 20,
  sort: 'updated_desc',
  include_archived: false
})

export const useInventoryStore = defineStore('inventory', {
  state: (): InventoryState => ({
    items: [],
    selectedItem: null,
    total: 0,
    page: 1,
    pageSize: 20,
    loading: false,
    saving: false,
    viewMode: 'cards',
    filters: defaultFilters()
  }),
  actions: {
    async loadItems(filters?: ItemFilters) {
      if (filters) {
        this.setFilters(filters)
      }
      this.loading = true
      try {
        const response = await listItemsApi(this.filters)
        this.items = response.items
        this.total = response.total
        this.page = response.page
        this.pageSize = response.page_size
      } finally {
        this.loading = false
      }
    },
    async openDetail(itemId: number) {
      this.loading = true
      try {
        this.selectedItem = await fetchItemDetailApi(itemId)
      } finally {
        this.loading = false
      }
    },
    async createItem(payload: ItemCreateRequest) {
      return await this.saveAndRefresh(() => createItemApi(payload))
    },
    async updateItem(itemId: number, payload: ItemUpdateRequest) {
      return await this.saveAndRefresh(() => updateItemApi(itemId, payload))
    },
    async archiveItem(itemId: number, payload: ArchiveItemRequest = {}) {
      return await this.saveAndRefresh(() => archiveItemApi(itemId, payload))
    },
    async moveItem(itemId: number, payload: MoveItemRequest) {
      return await this.saveAndRefresh(() => moveItemApi(itemId, payload))
    },
    async changeStatus(itemId: number, payload: ChangeStatusRequest) {
      return await this.saveAndRefresh(() => changeItemStatusApi(itemId, payload))
    },
    async adjustQuantity(itemId: number, payload: QuantityAdjustmentRequest) {
      return await this.saveAndRefresh(() => adjustQuantityApi(itemId, payload))
    },
    async borrowItem(itemId: number, payload: LoanCreateRequest) {
      return await this.saveAndRefresh(() => borrowItemApi(itemId, payload))
    },
    async returnLoan(itemId: number, loanId: number, payload: LoanReturnRequest) {
      return await this.saveAndRefresh(() => returnLoanApi(itemId, loanId, payload))
    },
    async uploadImage(itemId: number, file: File, isPrimary = false) {
      return await this.saveAndRefresh(() => uploadImageApi(itemId, file, isPrimary))
    },
    async uploadAttachment(itemId: number, file: File) {
      return await this.saveAndRefresh(() => uploadAttachmentApi(itemId, file))
    },
    async updateImage(itemId: number, imageId: number, payload: ItemImageUpdateRequest) {
      return await this.saveAndRefresh(() => updateImageApi(itemId, imageId, payload))
    },
    async deleteImage(itemId: number, imageId: number) {
      return await this.saveAndRefresh(() => deleteImageApi(itemId, imageId))
    },
    async deleteAttachment(itemId: number, attachmentId: number) {
      return await this.saveAndRefresh(() => deleteAttachmentApi(itemId, attachmentId))
    },
    closeDetail() {
      this.selectedItem = null
    },
    setFilters(filters: ItemFilters) {
      this.filters = { ...this.filters, ...filters }
    },
    resetFilters() {
      this.filters = defaultFilters()
    },
    async refreshSelectedItem() {
      if (this.selectedItem) {
        this.selectedItem = await fetchItemDetailApi(this.selectedItem.id)
      }
    },
    async saveAndRefresh<T>(operation: () => Promise<T>): Promise<T> {
      this.saving = true
      try {
        const result = await operation()
        await this.loadItems()
        await this.refreshSelectedItem()
        return result
      } finally {
        this.saving = false
      }
    }
  }
})
