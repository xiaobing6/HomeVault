<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { Grid, List, Plus, Search } from '@element-plus/icons-vue'

const props = defineProps<{
  search?: string | null
  viewMode: 'cards' | 'table'
  sort?: string
  canCreate: boolean
}>()

const emit = defineEmits<{
  'update:search': [value: string]
  'update:viewMode': [value: 'cards' | 'table']
  'update:sort': [value: string]
  search: []
  'add-item': []
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
