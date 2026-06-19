<script setup lang="ts">
import type { ItemSummary } from '../../api/inventory'

defineProps<{
  items: ItemSummary[]
}>()

const emit = defineEmits<{
  'open-detail': [itemId: number]
}>()
</script>

<template>
  <el-table
    :data="items"
    row-key="id"
    size="small"
    class="item-table"
    empty-text="还没有物品"
    @row-click="(row: ItemSummary) => emit('open-detail', row.id)"
  >
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
