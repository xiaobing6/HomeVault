<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'

import { getChineseErrorMessage } from '../api/client'
import type { ItemDetail, ItemLoan } from '../api/inventory'
import ItemActionDialogs from '../components/items/ItemActionDialogs.vue'
import ItemCardGrid from '../components/items/ItemCardGrid.vue'
import ItemDetailModal from '../components/items/ItemDetailModal.vue'
import ItemFilterPanel from '../components/items/ItemFilterPanel.vue'
import ItemFormDrawer from '../components/items/ItemFormDrawer.vue'
import ItemTable from '../components/items/ItemTable.vue'
import ItemToolbar from '../components/items/ItemToolbar.vue'
import { useAuthStore } from '../stores/auth'
import { useConfigurationStore } from '../stores/configuration'
import { useInventoryStore } from '../stores/inventory'

type ItemActionType = 'move' | 'status' | 'borrow' | 'return' | 'quantity' | 'archive'

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
  currentAction.value = action
  returnLoan.value = loan ?? null
  actionOpen.value = true
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
          @search="refreshSearch"
          @add-item="openCreateDrawer"
        />

        <ItemCardGrid
          v-if="viewMode === 'cards'"
          :items="items"
          @open-detail="openDetail"
        />
        <ItemTable v-else :items="items" @open-detail="openDetail" />

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
      @close="closeDetail"
    />

    <ItemActionDialogs
      v-model="actionOpen"
      :action="currentAction"
      :item="selectedItem"
      :return-loan="returnLoan"
      @success="handleActionSuccess"
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
