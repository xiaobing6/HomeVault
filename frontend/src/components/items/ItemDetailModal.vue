<script setup lang="ts">
import { computed } from 'vue'
import {
  Box,
  Edit,
  FolderRemove,
  Location,
  RefreshLeft,
  Sort,
  Switch,
  Tickets
} from '@element-plus/icons-vue'

import type {
  ItemDetail,
  ItemLoan,
  ItemMovement,
  ItemQuantityChange
} from '../../api/inventory'
import MediaUploader from './MediaUploader.vue'
import ProtectedImage from './ProtectedImage.vue'

const props = defineProps<{
  modelValue: boolean
  item: ItemDetail | null
  loading?: boolean
  canEdit: boolean
  canArchive: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  edit: []
  move: []
  status: []
  borrow: []
  return: [loan: ItemLoan]
  quantity: []
  archive: []
  close: []
}>()

const EXIT_STATUS_SEMANTICS = new Set(['removed', 'missing', 'consumed', 'retired', 'lost', 'disposed'])

const activeLoan = computed(() => {
  const loans = props.item?.loans ?? []
  return loans
    .filter((loan) => !loan.returned_at)
    .sort((left, right) =>
      new Date(right.loaned_at).getTime() - new Date(left.loaned_at).getTime() || right.id - left.id
    )[0] ?? null
})

const placementText = computed(() => {
  const item = props.item
  if (!item) return '未设置'
  if (item.container_item_name) return `容器：${item.container_item_name}`
  if (item.location_node_name) return `位置：${item.residence_name ? `${item.residence_name} / ` : ''}${item.location_node_name}`
  if (item.residence_name) return item.residence_name
  return '未设置'
})

const privacyLabel = computed(() => {
  const level = props.item?.privacy_level
  if (level === 'sensitive') return '敏感'
  return '普通'
})

const canMoveItem = computed(() => {
  const item = props.item
  if (!item) return false
  return !EXIT_STATUS_SEMANTICS.has(item.status_semantic)
})

const canBorrowItem = computed(() => {
  const item = props.item
  if (!item || activeLoan.value) return false
  return !EXIT_STATUS_SEMANTICS.has(item.status_semantic)
})

function updateOpen(open: boolean) {
  emit('update:modelValue', open)
  if (!open) emit('close')
}

function formatDateTime(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function formatDate(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('zh-CN')
}

function formatAttributeValue(value: string): string {
  const trimmedValue = value.trim()
  if (!trimmedValue) return '-'
  if (trimmedValue === 'true') return '是'
  if (trimmedValue === 'false') return '否'
  if (trimmedValue.startsWith('[')) {
    try {
      const parsedValue = JSON.parse(trimmedValue) as unknown
      if (Array.isArray(parsedValue)) return parsedValue.join('、') || '-'
    } catch {
      return value
    }
  }
  return value
}

function movementTypeLabel(type: string): string {
  if (type === 'move') return '移动'
  if (type === 'status') return '状态'
  if (type === 'create') return '创建'
  return type || '-'
}

function movementTarget(row: ItemMovement): string {
  if (row.new_container_item_name) return `容器：${row.new_container_item_name}`
  if (row.new_location_node_name) return `位置：${row.new_location_node_name}`
  return '无'
}

function movementSource(row: ItemMovement): string {
  if (row.previous_container_item_name) return `容器：${row.previous_container_item_name}`
  if (row.previous_location_node_name) return `位置：${row.previous_location_node_name}`
  return '无'
}

function quantityText(row: ItemQuantityChange): string {
  return `${row.quantity_before} → ${row.quantity_after}（${row.quantity_delta}）`
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    width="min(960px, 96vw)"
    top="5vh"
    class="item-detail-dialog"
    destroy-on-close
    @update:model-value="updateOpen"
  >
    <template #header>
      <div class="dialog-header">
        <div>
          <h2>{{ item?.name || '物品详情' }}</h2>
          <p>{{ item?.category_name || '未分类' }}</p>
        </div>
        <el-tag v-if="item?.is_archived" type="info">已归档</el-tag>
        <el-tag v-else-if="item?.status_name" effect="plain">{{ item.status_name }}</el-tag>
      </div>
    </template>

    <div v-loading="loading" class="detail-body">
      <el-empty v-if="!item" description="暂无详情" />

      <template v-else>
        <div class="action-bar">
          <el-button
            v-if="canEdit && !item.is_archived"
            type="primary"
            :icon="Edit"
            @click="emit('edit')"
          >
            编辑
          </el-button>
          <el-button
            v-if="canEdit && !item.is_archived && canMoveItem"
            :icon="Location"
            @click="emit('move')"
          >
            移动
          </el-button>
          <el-button
            v-if="canEdit && !item.is_archived"
            :icon="Switch"
            @click="emit('status')"
          >
            状态
          </el-button>
          <el-button
            v-if="canEdit && !item.is_archived && canBorrowItem"
            :icon="Tickets"
            @click="emit('borrow')"
          >
            借出
          </el-button>
          <el-button
            v-if="canEdit && !item.is_archived && activeLoan"
            :icon="RefreshLeft"
            @click="emit('return', activeLoan)"
          >
            归还
          </el-button>
          <el-button
            v-if="canEdit && !item.is_archived"
            :icon="Sort"
            @click="emit('quantity')"
          >
            调整数量
          </el-button>
          <el-button
            v-if="canArchive && !item.is_archived"
            type="danger"
            plain
            :icon="FolderRemove"
            @click="emit('archive')"
          >
            归档
          </el-button>
        </div>

        <el-tabs>
          <el-tab-pane label="概览">
            <div class="overview-layout">
              <div class="overview-image">
                <ProtectedImage
                  v-if="item.primary_image_url"
                  :src="item.primary_image_url"
                  :alt="item.name"
                >
                  <el-icon><Box /></el-icon>
                </ProtectedImage>
                <el-icon v-else><Box /></el-icon>
              </div>

              <el-descriptions :column="2" border>
                <el-descriptions-item label="名称">{{ item.name }}</el-descriptions-item>
                <el-descriptions-item label="分类">{{ item.category_name || '-' }}</el-descriptions-item>
                <el-descriptions-item label="状态">{{ item.status_name || '-' }}</el-descriptions-item>
                <el-descriptions-item label="数量">{{ item.quantity }} {{ item.unit }}</el-descriptions-item>
                <el-descriptions-item label="位置">{{ placementText }}</el-descriptions-item>
                <el-descriptions-item label="容器">
                  {{ item.is_container ? '是' : '否' }}
                </el-descriptions-item>
                <el-descriptions-item label="归属人">
                  {{ item.owner_member_name || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="保管人">
                  {{ item.keeper_member_name || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="隐私">{{ privacyLabel }}</el-descriptions-item>
                <el-descriptions-item label="更新时间">
                  {{ formatDateTime(item.updated_at) }}
                </el-descriptions-item>
                <el-descriptions-item label="说明" :span="2">
                  {{ item.description || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="标签" :span="2">
                  <div v-if="item.tags.length > 0" class="tag-list">
                    <el-tag v-for="tag in item.tags" :key="tag.id" effect="plain">
                      {{ tag.name }}
                    </el-tag>
                  </div>
                  <span v-else>-</span>
                </el-descriptions-item>
                <el-descriptions-item v-if="item.is_archived" label="归档原因" :span="2">
                  {{ item.archive_reason || '-' }}
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </el-tab-pane>

          <el-tab-pane label="自定义字段">
            <el-table
              :data="item.attribute_values"
              size="small"
              empty-text="暂无自定义字段"
            >
              <el-table-column prop="attribute_name" label="字段" min-width="160" />
              <el-table-column label="内容" min-width="220" show-overflow-tooltip>
                <template #default="{ row }">
                  {{ formatAttributeValue(row.value) }}
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="图片和附件">
            <MediaUploader
              :images="item.images"
              :attachments="item.attachments"
              :image-files="[]"
              :attachment-files="[]"
              :editable="false"
            />
          </el-tab-pane>

          <el-tab-pane label="移动记录">
            <el-table :data="item.movements" size="small" empty-text="暂无移动记录">
              <el-table-column label="类型" width="90">
                <template #default="{ row }">{{ movementTypeLabel(row.movement_type) }}</template>
              </el-table-column>
              <el-table-column label="原位置" min-width="150" show-overflow-tooltip>
                <template #default="{ row }">{{ movementSource(row) }}</template>
              </el-table-column>
              <el-table-column label="新位置" min-width="150" show-overflow-tooltip>
                <template #default="{ row }">{{ movementTarget(row) }}</template>
              </el-table-column>
              <el-table-column label="状态变化" min-width="150" show-overflow-tooltip>
                <template #default="{ row }">
                  {{ row.previous_status_name || '-' }} → {{ row.new_status_name || '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="reason" label="原因" min-width="150" show-overflow-tooltip />
              <el-table-column label="时间" width="180">
                <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="数量记录">
            <el-table :data="item.quantity_changes" size="small" empty-text="暂无数量记录">
              <el-table-column label="变化" min-width="190">
                <template #default="{ row }">{{ quantityText(row) }} {{ row.unit }}</template>
              </el-table-column>
              <el-table-column prop="reason" label="原因" min-width="150" show-overflow-tooltip />
              <el-table-column prop="note" label="备注" min-width="160" show-overflow-tooltip />
              <el-table-column label="时间" width="180">
                <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="借用记录">
            <el-table :data="item.loans" size="small" empty-text="暂无借用记录">
              <el-table-column prop="borrower_name" label="借用人" min-width="120" />
              <el-table-column prop="borrower_contact" label="联系方式" min-width="140" show-overflow-tooltip />
              <el-table-column label="预计归还" width="120">
                <template #default="{ row }">{{ formatDate(row.expected_return_date) }}</template>
              </el-table-column>
              <el-table-column label="借出时间" width="180">
                <template #default="{ row }">{{ formatDateTime(row.loaned_at) }}</template>
              </el-table-column>
              <el-table-column label="归还时间" width="180">
                <template #default="{ row }">{{ formatDateTime(row.returned_at) }}</template>
              </el-table-column>
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag v-if="row.returned_at" size="small" type="success">已归还</el-tag>
                  <el-tag v-else size="small" type="warning">未归还</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </template>
    </div>
  </el-dialog>
</template>

<style scoped>
.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.dialog-header h2 {
  margin: 0;
  color: #25342d;
  font-size: 18px;
}

.dialog-header p {
  margin: 4px 0 0;
  color: #68756d;
  font-size: 13px;
}

.detail-body {
  min-height: 320px;
}

.action-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.overview-layout {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 16px;
  min-width: 0;
}

.overview-image {
  display: grid;
  width: 180px;
  aspect-ratio: 1;
  place-items: center;
  overflow: hidden;
  color: #779182;
  background: #eef5ef;
  border-radius: 8px;
}

.overview-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.overview-image .el-icon {
  font-size: 42px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

@media (max-width: 720px) {
  .overview-layout {
    grid-template-columns: 1fr;
  }

  .overview-image {
    width: 100%;
    max-width: 240px;
  }
}
</style>
