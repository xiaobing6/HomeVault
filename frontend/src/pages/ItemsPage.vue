<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'

import { getChineseErrorMessage } from '../api/client'
import ItemCardGrid from '../components/items/ItemCardGrid.vue'
import ItemFilterPanel from '../components/items/ItemFilterPanel.vue'
import ItemTable from '../components/items/ItemTable.vue'
import ItemToolbar from '../components/items/ItemToolbar.vue'
import { useAuthStore } from '../stores/auth'
import { useConfigurationStore } from '../stores/configuration'
import { useInventoryStore } from '../stores/inventory'

const auth = useAuthStore()
const configuration = useConfigurationStore()
const inventory = useInventoryStore()
const { items, loading, total, page, pageSize, viewMode } = storeToRefs(inventory)

const createPlaceholderOpen = ref(false)
const detailPlaceholderId = ref<number | null>(null)

const canCreate = computed(() => auth.hasPermission('items:create'))
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
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
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
  detailPlaceholderId.value = itemId
  try {
    await inventory.openDetail(itemId)
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

function openCreatePlaceholder() {
  createPlaceholderOpen.value = true
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
          @add-item="openCreatePlaceholder"
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
