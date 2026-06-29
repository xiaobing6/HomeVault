<script setup lang="ts">
import { ref, watch } from 'vue'
import type { TableInstance } from 'element-plus'
import type { ItemSummary } from '../../api/inventory'

const props = defineProps<{
  items: ItemSummary[]
  selectedItemIds?: number[]
}>()

const emit = defineEmits<{
  'open-detail': [itemId: number]
  'selection-change': [items: ItemSummary[]]
}>()

const tableRef = ref<TableInstance>()

function handleRowClick(row: ItemSummary, column?: { type?: string }) {
  if (column?.type === 'selection') return
  emit('open-detail', row.id)
}

watch(
  [() => props.items, () => props.selectedItemIds],
  () => {
    const table = tableRef.value
    if (!table) return
    const selectedIds = new Set(props.selectedItemIds ?? [])
    props.items.forEach((item) => {
      table.toggleRowSelection(item, selectedIds.has(item.id))
    })
  },
  { flush: 'post', deep: true }
)
</script>

<template>
  <el-table
    ref="tableRef"
    :data="items"
    row-key="id"
    size="small"
    class="item-table"
    empty-text="还没有物品"
    @selection-change="(selection: ItemSummary[]) => emit('selection-change', selection)"
    @row-click="handleRowClick"
  >
    <el-table-column type="selection" width="48" reserve-selection />
    <el-table-column label="物品" min-width="190" show-overflow-tooltip>
      <template #default="{ row }">
        <div class="name-cell">
          <span>{{ row.name }}</span>
          <el-tag v-if="row.is_container" size="small" type="success">容器</el-tag>
        </div>
      </template>
    </el-table-column>
    <el-table-column prop="category_name" label="分类" min-width="120" show-overflow-tooltip />
    <el-table-column label="位置" min-width="150" show-overflow-tooltip>
      <template #default="{ row }">
        {{ row.location_node_name || row.residence_name || '未设置' }}
      </template>
    </el-table-column>
    <el-table-column label="状态" width="112">
      <template #default="{ row }">
        <el-tag v-if="row.is_archived" size="small" type="info">已归档</el-tag>
        <el-tag v-else size="small" effect="plain">{{ row.status_name }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="数量" width="108">
      <template #default="{ row }">{{ row.quantity }} {{ row.unit }}</template>
    </el-table-column>
    <el-table-column label="保管人" min-width="120" show-overflow-tooltip>
      <template #default="{ row }">
        {{ row.keeper_member_name || row.owner_member_name || '未设置' }}
      </template>
    </el-table-column>
    <el-table-column prop="updated_at" label="更新时间" width="170" show-overflow-tooltip />
  </el-table>
</template>

<style scoped>
.item-table {
  width: 100%;
  border: 1px solid #e2e8df;
  border-radius: 8px;
}

.item-table :deep(.el-table__row) {
  cursor: pointer;
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.name-cell span {
  min-width: 0;
  overflow: hidden;
  color: #25342d;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
