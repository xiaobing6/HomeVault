<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { Download, Grid, List, Operation, Plus, Search, Upload } from '@element-plus/icons-vue'

const props = defineProps<{
  search?: string | null
  viewMode: 'cards' | 'table'
  sort?: string
  canCreate: boolean
  canEdit: boolean
  canArchive: boolean
  selectedCount: number
  exporting?: boolean
}>()

const emit = defineEmits<{
  'update:search': [value: string]
  'update:viewMode': [value: 'cards' | 'table']
  'update:sort': [value: string]
  search: []
  'add-item': []
  'bulk-move': []
  'bulk-status': []
  'bulk-archive': []
  'export-selected': []
  'export-filtered': []
  'import-items': []
}>()

const localSearch = ref(props.search ?? '')
let searchTimer: number | undefined

const sortOptions = [
  { label: '最近更新', value: 'updated_desc' },
  { label: '最早更新', value: 'updated_asc' },
  { label: '名称 A-Z', value: 'name_asc' },
  { label: '名称 Z-A', value: 'name_desc' },
  { label: '最近创建', value: 'created_desc' }
]

watch(
  () => props.search,
  (value) => {
    if ((value ?? '') !== localSearch.value) localSearch.value = value ?? ''
  }
)

watch(localSearch, (value) => {
  emit('update:search', value)
  clearPendingSearch()
  searchTimer = window.setTimeout(() => emit('search'), 350)
}, { flush: 'sync' })

onUnmounted(() => {
  clearPendingSearch()
})

function clearPendingSearch() {
  window.clearTimeout(searchTimer)
  searchTimer = undefined
}

function submitSearchNow() {
  clearPendingSearch()
  emit('search')
}
</script>

<template>
  <div class="item-toolbar">
    <el-input
      v-model="localSearch"
      class="search-input"
      :prefix-icon="Search"
      placeholder="搜索物品"
      clearable
      @keyup.enter="submitSearchNow"
      @clear="submitSearchNow"
    />

    <div class="toolbar-actions">
      <el-segmented
        :model-value="viewMode"
        :options="[
          { label: '卡片', value: 'cards', icon: Grid },
          { label: '表格', value: 'table', icon: List }
        ]"
        @update:model-value="emit('update:viewMode', $event as 'cards' | 'table')"
      />

      <el-select
        :model-value="sort"
        class="sort-select"
        @update:model-value="emit('update:sort', $event)"
      >
        <el-option
          v-for="option in sortOptions"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </el-select>

      <el-dropdown
        :disabled="selectedCount === 0 || (!canEdit && !canArchive)"
        trigger="click"
      >
        <el-button :icon="Operation" :disabled="selectedCount === 0 || (!canEdit && !canArchive)">
          批量 {{ selectedCount ? `(${selectedCount})` : '' }}
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item v-if="canEdit" @click="emit('bulk-move')">批量移动</el-dropdown-item>
            <el-dropdown-item v-if="canEdit" @click="emit('bulk-status')">批量改状态</el-dropdown-item>
            <el-dropdown-item v-if="canArchive" divided @click="emit('bulk-archive')">批量归档</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <el-dropdown trigger="click">
        <el-button :icon="Download" :loading="exporting">
          导出
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="emit('export-filtered')">导出当前筛选</el-dropdown-item>
            <el-dropdown-item
              :disabled="selectedCount === 0"
              @click="selectedCount > 0 && emit('export-selected')"
            >
              导出已选
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <el-button v-if="canCreate" :icon="Upload" @click="emit('import-items')">
        导入
      </el-button>

      <el-button v-if="canCreate" type="primary" :icon="Plus" @click="emit('add-item')">
        新增
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.item-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
  padding: 12px;
  background: #fff;
  border: 1px solid #e2e8df;
  border-radius: 8px;
}

.search-input {
  width: min(360px, 100%);
}

.toolbar-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  min-width: 0;
}

.sort-select {
  width: 136px;
}

@media (max-width: 760px) {
  .item-toolbar,
  .toolbar-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .search-input,
  .sort-select {
    width: 100%;
  }
}
</style>
