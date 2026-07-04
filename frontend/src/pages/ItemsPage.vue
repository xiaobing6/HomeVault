<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'

import { getChineseErrorMessage } from '../api/client'
import type { BulkItemOperationResponse, ItemDetail, ItemLoan, ItemSummary } from '../api/inventory'
import BulkActionDialogs from '../components/items/BulkActionDialogs.vue'
import ItemActionDialogs from '../components/items/ItemActionDialogs.vue'
import ItemCardGrid from '../components/items/ItemCardGrid.vue'
import ItemDetailModal from '../components/items/ItemDetailModal.vue'
import ItemFilterPanel from '../components/items/ItemFilterPanel.vue'
import ItemFormDrawer from '../components/items/ItemFormDrawer.vue'
import ItemImportDialog from '../components/items/ItemImportDialog.vue'
import ItemTable from '../components/items/ItemTable.vue'
import ItemToolbar from '../components/items/ItemToolbar.vue'
import { useAuthStore } from '../stores/auth'
import { useConfigurationStore } from '../stores/configuration'
import { useInventoryStore } from '../stores/inventory'

type ItemActionType = 'move' | 'status' | 'borrow' | 'return' | 'quantity' | 'archive' | 'delete'
type BulkActionType = 'move' | 'status' | 'archive' | 'delete'

const auth = useAuthStore()
const configuration = useConfigurationStore()
const inventory = useInventoryStore()
const route = useRoute()
const { items, loading, selectedItem, total, page, pageSize, viewMode } = storeToRefs(inventory)

const canCreate = computed(() => auth.hasPermission('items:create'))
const canEdit = computed(() => auth.hasPermission('items:edit'))
const canArchive = computed(() => auth.hasPermission('items:archive'))
const detailOpen = ref(false)
const formOpen = ref(false)
const editingItem = ref<ItemDetail | null>(null)
const actionOpen = ref(false)
const currentAction = ref<ItemActionType | null>(null)
const returnLoan = ref<ItemLoan | null>(null)
const selectedItems = ref<ItemSummary[]>([])
const bulkActionOpen = ref(false)
const currentBulkAction = ref<BulkActionType | null>(null)
const exporting = ref(false)
const importDialogOpen = ref(false)
const importTemplateDownloading = ref(false)
const selectedItemIds = computed(() => selectedItems.value.map((item) => item.id))
const selectedCount = computed(() => selectedItems.value.length)
const searchValue = computed({
  get: () => inventory.filters.search ?? '',
  set: (value: string) => {
    inventory.applyFilters({ search: value.trim() || null })
  }
})
const sortValue = computed({
  get: () => inventory.filters.sort ?? 'updated_desc',
  set: (value: string) => {
    void applyAndLoad({ sort: value })
  }
})

onMounted(async () => {
  try {
    await Promise.all([configuration.load(), inventory.loadItems()])
    await openRouteItemDetail()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
})

watch(
  () => route.query.item_id,
  () => {
    void openRouteItemDetail()
  }
)

watch(items, (nextItems) => {
  const visibleIds = new Set(nextItems.map((item) => item.id))
  selectedItems.value = selectedItems.value.filter((item) => visibleIds.has(item.id))
})

async function applyAndLoad(filters: Parameters<typeof inventory.applyFilters>[0]) {
  try {
    inventory.applyFilters(filters)
    await inventory.loadItems()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function refreshSearch() {
  await applyAndLoad({ search: searchValue.value.trim() || null })
}

async function changePage(nextPage: number) {
  try {
    inventory.setPage(nextPage)
    await inventory.loadItems()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function changePageSize(nextSize: number) {
  try {
    inventory.setPageSize(nextSize)
    await inventory.loadItems()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function openDetail(itemId: number) {
  try {
    await inventory.openDetail(itemId)
    detailOpen.value = true
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

function routeItemId(): number | null {
  const rawItemId = Array.isArray(route.query.item_id) ? route.query.item_id[0] : route.query.item_id
  if (!rawItemId) return null

  const itemId = Number(rawItemId)
  return Number.isInteger(itemId) && itemId > 0 ? itemId : null
}

async function openRouteItemDetail() {
  const itemId = routeItemId()
  if (!itemId) return
  await openDetail(itemId)
}

function openCreateDrawer() {
  if (!canCreate.value) return
  editingItem.value = null
  formOpen.value = true
}

function openEditDrawer() {
  if (!selectedItem.value || !canEdit.value) return
  editingItem.value = selectedItem.value
  formOpen.value = true
}

function openActionDialog(action: ItemActionType, loan?: ItemLoan) {
  if (!selectedItem.value) return
  if ((action === 'archive' || action === 'delete') && !canArchive.value) return
  if (!['archive', 'delete'].includes(action) && !canEdit.value) return
  currentAction.value = action
  returnLoan.value = loan ?? null
  actionOpen.value = true
}

function handleSelectionChange(selection: ItemSummary[]) {
  selectedItems.value = selection
}

function openBulkAction(action: BulkActionType) {
  if (selectedItemIds.value.length === 0) {
    ElMessage.warning('请先选择物品')
    return
  }
  if ((action === 'move' || action === 'status') && !canEdit.value) return
  if ((action === 'archive' || action === 'delete') && !canArchive.value) return
  currentBulkAction.value = action
  bulkActionOpen.value = true
}

async function refreshListAndDetail(itemId: number) {
  try {
    await inventory.loadItems()
    await inventory.openDetail(itemId)
    detailOpen.value = true
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function handleFormSaved(detail: ItemDetail) {
  editingItem.value = null
  await refreshListAndDetail(detail.id)
}

async function handleActionSuccess(detail: ItemDetail) {
  await refreshListAndDetail(detail.id)
}

async function handleDeleteSuccess(_detail: ItemDetail) {
  detailOpen.value = false
  inventory.closeDetail()
  await inventory.loadItems()
}

async function handleDialogSuccess(detail: ItemDetail) {
  if (currentAction.value === 'delete') {
    await handleDeleteSuccess(detail)
    return
  }
  await handleActionSuccess(detail)
}

function handleBulkSuccess(_response: BulkItemOperationResponse) {
  selectedItems.value = []
}

function downloadCsvBlob(blob: Blob, scope: 'filtered' | 'selected') {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `homevault-items-${scope}-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function downloadImportTemplateBlob(blob: Blob) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `homevault-import-template-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

async function exportFilteredItems() {
  exporting.value = true
  try {
    const blob = await inventory.exportItemsCsv({ filters: { ...inventory.filters } })
    downloadCsvBlob(blob, 'filtered')
    ElMessage.success('已导出当前筛选')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    exporting.value = false
  }
}

async function exportSelectedItems() {
  if (selectedItemIds.value.length === 0) {
    ElMessage.warning('请先选择物品')
    return
  }
  exporting.value = true
  try {
    const blob = await inventory.exportItemsCsv({ item_ids: selectedItemIds.value })
    downloadCsvBlob(blob, 'selected')
    ElMessage.success('已导出已选物品')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    exporting.value = false
  }
}

async function downloadImportTemplate() {
  if (importTemplateDownloading.value) return

  importTemplateDownloading.value = true
  try {
    const blob = await inventory.downloadImportTemplate()
    downloadImportTemplateBlob(blob)
    ElMessage.success('已下载导入模板')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    importTemplateDownloading.value = false
  }
}

function handleImportDone() {
  selectedItems.value = []
}

function closeDetail() {
  detailOpen.value = false
  inventory.closeDetail()
}
</script>

<template>
  <section class="items-page" v-loading="loading">
    <h1 class="page-title">物品</h1>

    <div class="workbench-layout">
      <ItemFilterPanel class="filters" />

      <div class="work-area">
        <ItemToolbar
          v-model:search="searchValue"
          v-model:view-mode="viewMode"
          v-model:sort="sortValue"
          :can-create="canCreate"
          :can-edit="canEdit"
          :can-archive="canArchive"
          :selected-count="selectedCount"
          :exporting="exporting"
          @search="refreshSearch"
          @add-item="openCreateDrawer"
          @bulk-move="openBulkAction('move')"
          @bulk-status="openBulkAction('status')"
          @bulk-archive="openBulkAction('archive')"
          @bulk-delete="openBulkAction('delete')"
          @export-filtered="exportFilteredItems"
          @export-selected="exportSelectedItems"
          @import-items="importDialogOpen = true"
        />

        <ItemCardGrid
          v-if="viewMode === 'cards'"
          :items="items"
          @open-detail="openDetail"
        />
        <ItemTable
          v-else
          :items="items"
          :selected-item-ids="selectedItemIds"
          @selection-change="handleSelectionChange"
          @open-detail="openDetail"
        />

        <div class="pagination-row">
          <el-pagination
            background
            layout="total, sizes, prev, pager, next"
            :total="total"
            :current-page="page"
            :page-size="pageSize"
            :page-sizes="[12, 20, 40, 80]"
            @current-change="changePage"
            @size-change="changePageSize"
          />
        </div>
      </div>
    </div>

    <ItemFormDrawer
      v-model="formOpen"
      :item="editingItem"
      @saved="handleFormSaved"
    />

    <ItemDetailModal
      v-model="detailOpen"
      :item="selectedItem"
      :loading="loading"
      :can-edit="canEdit"
      :can-archive="canArchive"
      @edit="openEditDrawer"
      @move="openActionDialog('move')"
      @status="openActionDialog('status')"
      @borrow="openActionDialog('borrow')"
      @return="(loan) => openActionDialog('return', loan)"
      @quantity="openActionDialog('quantity')"
      @archive="openActionDialog('archive')"
      @delete="openActionDialog('delete')"
      @close="closeDetail"
    />

    <ItemActionDialogs
      v-model="actionOpen"
      :action="currentAction"
      :item="selectedItem"
      :return-loan="returnLoan"
      @success="handleDialogSuccess"
    />

    <BulkActionDialogs
      v-model="bulkActionOpen"
      :action="currentBulkAction"
      :selected-item-ids="selectedItemIds"
      :selected-count="selectedCount"
      @success="handleBulkSuccess"
    />

    <ItemImportDialog
      v-model="importDialogOpen"
      @download-template="downloadImportTemplate"
      @imported="handleImportDone"
    />
  </section>
</template>

<style scoped>
.items-page {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.workbench-layout {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  align-items: start;
  gap: 16px;
  min-width: 0;
}

.filters {
  position: sticky;
  top: 16px;
}

.work-area {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.pagination-row {
  display: flex;
  justify-content: flex-end;
  min-width: 0;
  padding: 12px;
  overflow-x: auto;
  background: #fff;
  border: 1px solid #e2e8df;
  border-radius: 8px;
}

@media (max-width: 980px) {
  .workbench-layout {
    grid-template-columns: 1fr;
  }

  .filters {
    position: static;
  }
}
</style>
