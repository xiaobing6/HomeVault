<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { Folder, HomeFilled, Location, RefreshLeft } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../../api/client'
import type { Category, LocationNode, Residence } from '../../api/configuration'
import { useConfigurationStore } from '../../stores/configuration'
import { useInventoryStore } from '../../stores/inventory'
import { dictionaryOptions } from '../../utils/dictionaries'

interface FilterTreeNode {
  id: string
  label: string
  type: 'residence' | 'location' | 'category'
  value: number
  residenceId?: number
  children?: FilterTreeNode[]
}

const configuration = useConfigurationStore()
const inventory = useInventoryStore()
const { data } = storeToRefs(configuration)

const locationSelectedKey = computed(() => {
  if (inventory.filters.location_node_id) return `location-${inventory.filters.location_node_id}`
  if (inventory.filters.residence_id) return `residence-${inventory.filters.residence_id}`
  return ''
})

const categorySelectedKey = computed(() =>
  inventory.filters.category_id ? `category-${inventory.filters.category_id}` : ''
)
const importanceOptions = computed(() => dictionaryOptions(data.value, 'importance'))

const importanceValue = computed({
  get: () => inventory.filters.importance ?? '',
  set: (value: string) => {
    void applyFilters({ importance: value || null })
  }
})

const quickFilters = computed({
  get: () => [
    ...(inventory.filters.is_on_loan ? ['loan'] : []),
    ...(inventory.filters.has_pending_reminder ? ['reminder-pending'] : []),
    ...(inventory.filters.has_upcoming_reminder ? ['reminder-upcoming'] : []),
    ...(inventory.filters.has_overdue_reminder ? ['reminder-overdue'] : []),
    ...(inventory.filters.container_only ? ['container'] : []),
    ...(inventory.filters.include_archived ? ['archived'] : [])
  ],
  set: (values: string[]) => {
    void applyFilters({
      is_on_loan: values.includes('loan') ? true : null,
      has_pending_reminder: values.includes('reminder-pending') ? true : null,
      has_upcoming_reminder: values.includes('reminder-upcoming') ? true : null,
      has_overdue_reminder: values.includes('reminder-overdue') ? true : null,
      reminder_upcoming_days: 7,
      container_only: values.includes('container') ? true : null,
      include_archived: values.includes('archived')
    })
  }
})

const locationTree = computed<FilterTreeNode[]>(() => {
  const residences = data.value?.residences ?? []
  const nodes = data.value?.location_tree ?? []
  return residences.map((residence) => toResidenceNode(residence, nodes))
})

const categoryTree = computed<FilterTreeNode[]>(() =>
  (data.value?.categories ?? []).map((category) => toCategoryNode(category))
)

function toResidenceNode(residence: Residence, nodes: LocationNode[]): FilterTreeNode {
  return {
    id: `residence-${residence.id}`,
    label: residence.name,
    type: 'residence',
    value: residence.id,
    children: nodes
      .filter((node) => node.residence_id === residence.id)
      .map((node) => toLocationNode(node, residence.id))
  }
}

function toLocationNode(node: LocationNode, residenceId: number): FilterTreeNode {
  return {
    id: `location-${node.id}`,
    label: node.name,
    type: 'location',
    value: node.id,
    residenceId,
    children: (node.children ?? []).map((child) => toLocationNode(child, residenceId))
  }
}

function toCategoryNode(category: Category): FilterTreeNode {
  return {
    id: `category-${category.id}`,
    label: category.name,
    type: 'category',
    value: category.id,
    children: (category.children ?? []).map((child) => toCategoryNode(child))
  }
}

async function applyFilters(filters: Parameters<typeof inventory.applyFilters>[0]) {
  try {
    inventory.applyFilters(filters)
    await inventory.loadItems()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

function selectLocation(node: FilterTreeNode) {
  if (node.type === 'residence') {
    void applyFilters({ residence_id: node.value, location_node_id: null })
  }
  if (node.type === 'location') {
    void applyFilters({
      residence_id: node.residenceId ?? null,
      location_node_id: node.value
    })
  }
}

function selectCategory(node: FilterTreeNode) {
  if (node.type !== 'category') return
  void applyFilters({ category_id: node.value })
}

async function resetFilters() {
  try {
    inventory.resetFilters()
    await inventory.loadItems()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}
</script>

<template>
  <aside class="filter-panel">
    <div class="filter-header">
      <h2>筛选</h2>
      <el-button text :icon="RefreshLeft" @click="resetFilters">重置</el-button>
    </div>

    <section class="filter-section">
      <div class="section-title">
        <el-icon><HomeFilled /></el-icon>
        <span>位置</span>
      </div>
      <el-tree
        :data="locationTree"
        node-key="id"
        :current-node-key="locationSelectedKey"
        highlight-current
        default-expand-all
        empty-text="暂无位置"
        @node-click="selectLocation"
      />
    </section>

    <section class="filter-section">
      <div class="section-title">
        <el-icon><Folder /></el-icon>
        <span>分类</span>
      </div>
      <el-tree
        :data="categoryTree"
        node-key="id"
        :current-node-key="categorySelectedKey"
        highlight-current
        default-expand-all
        empty-text="暂无分类"
        @node-click="selectCategory"
      />
    </section>

    <section class="filter-section">
      <div class="section-title">
        <el-icon><Location /></el-icon>
        <span>Importance</span>
      </div>
      <el-select v-model="importanceValue" clearable class="full-width">
        <el-option
          v-for="option in importanceOptions"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </el-select>
    </section>

    <section class="filter-section">
      <div class="section-title">
        <el-icon><Location /></el-icon>
        <span>快捷筛选</span>
      </div>
      <el-checkbox-group v-model="quickFilters" class="quick-filters">
        <el-checkbox-button label="loan">借出未归还</el-checkbox-button>
        <el-checkbox-button label="reminder-pending">有待处理提醒</el-checkbox-button>
        <el-checkbox-button label="reminder-upcoming">即将到期</el-checkbox-button>
        <el-checkbox-button label="reminder-overdue">已逾期</el-checkbox-button>
        <el-checkbox-button label="container">容器物品</el-checkbox-button>
        <el-checkbox-button label="archived">已归档</el-checkbox-button>
      </el-checkbox-group>
    </section>
  </aside>
</template>

<style scoped>
.filter-panel {
  display: grid;
  align-content: start;
  gap: 16px;
  min-width: 0;
  padding: 16px;
  background: #fff;
  border: 1px solid #e2e8df;
  border-radius: 8px;
}

.filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.filter-header h2 {
  margin: 0;
  color: #25342d;
  font-size: 16px;
}

.filter-section {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.full-width {
  width: 100%;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #536258;
  font-size: 13px;
  font-weight: 700;
}

.filter-section :deep(.el-tree) {
  --el-tree-node-hover-bg-color: #eef5ef;
  max-height: 280px;
  overflow: auto;
  color: #2d3932;
  background: transparent;
}

.quick-filters {
  display: grid;
  gap: 8px;
}

.quick-filters :deep(.el-checkbox-button__inner) {
  width: 100%;
  border-left: var(--el-border);
  border-radius: 6px;
  text-align: left;
}
</style>
