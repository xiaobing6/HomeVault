<script setup lang="ts">
import { computed } from 'vue'
import {
  Bell,
  Check,
  CloseBold,
  Delete,
  Edit,
  RefreshLeft
} from '@element-plus/icons-vue'

import type { ReminderDetail, ReminderDueState, ReminderPriority, ReminderSourceType, ReminderStatus } from '../../api/reminders'
import { formatReminderDate } from '../../utils/reminderDates'

const props = defineProps<{
  modelValue: boolean
  reminder: ReminderDetail | null
  loading?: boolean
  saving?: boolean
  canEdit: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  edit: []
  complete: []
  dismiss: []
  reopen: []
  archive: []
  close: []
}>()

const isArchived = computed(() => Boolean(props.reminder?.archived_at))
const canMutate = computed(() => props.canEdit && !isArchived.value)
const canEditManual = computed(() => canMutate.value && props.reminder?.source_type === 'manual')

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

function sourceLabel(value?: ReminderSourceType): string {
  if (value === 'loan_return') return '借出归还'
  if (value === 'manual') return '手动提醒'
  return '-'
}

function statusLabel(value?: ReminderStatus): string {
  if (value === 'pending') return '待处理'
  if (value === 'done') return '已完成'
  if (value === 'dismissed') return '已忽略'
  return '-'
}

function statusTagType(value?: ReminderStatus): 'success' | 'warning' | 'info' {
  if (value === 'done') return 'success'
  if (value === 'pending') return 'warning'
  return 'info'
}

function dueStateLabel(value?: ReminderDueState): string {
  if (value === 'overdue') return '已逾期'
  if (value === 'upcoming') return '即将到期'
  if (value === 'scheduled') return '已安排'
  if (value === 'pending') return '待处理'
  if (value === 'done') return '已完成'
  if (value === 'dismissed') return '已忽略'
  if (value === 'none') return '无日期'
  return '-'
}

function dueStateTagType(value?: ReminderDueState): 'danger' | 'warning' | 'success' | 'info' {
  if (value === 'overdue') return 'danger'
  if (value === 'upcoming' || value === 'pending') return 'warning'
  if (value === 'done') return 'success'
  return 'info'
}

function priorityLabel(value?: ReminderPriority): string {
  if (value === 'high') return '高'
  if (value === 'low') return '低'
  if (value === 'normal') return '普通'
  return '-'
}

function priorityTagType(value?: ReminderPriority): 'danger' | 'warning' | 'info' {
  if (value === 'high') return 'danger'
  if (value === 'low') return 'info'
  return 'warning'
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    width="min(820px, 96vw)"
    top="7vh"
    class="reminder-detail-dialog"
    destroy-on-close
    @update:model-value="updateOpen"
  >
    <template #header>
      <div class="dialog-header">
        <div>
          <h2>{{ reminder?.title || '提醒详情' }}</h2>
          <p>{{ reminder?.item?.name || '未关联物品' }}</p>
        </div>
        <el-tag v-if="isArchived" type="info">已归档</el-tag>
        <el-tag v-else :type="statusTagType(reminder?.status)" effect="plain">
          {{ statusLabel(reminder?.status) }}
        </el-tag>
      </div>
    </template>

    <div v-loading="loading" class="detail-body">
      <el-empty v-if="!reminder" description="暂无提醒详情" />

      <template v-else>
        <div class="action-bar">
          <el-button
            v-if="canEditManual"
            type="primary"
            :icon="Edit"
            :loading="saving"
            @click="emit('edit')"
          >
            编辑
          </el-button>
          <el-button
            v-if="canMutate && reminder.status === 'pending'"
            type="success"
            plain
            :icon="Check"
            :loading="saving"
            @click="emit('complete')"
          >
            完成
          </el-button>
          <el-button
            v-if="canMutate && reminder.status === 'pending'"
            plain
            :icon="CloseBold"
            :loading="saving"
            @click="emit('dismiss')"
          >
            忽略
          </el-button>
          <el-button
            v-if="canMutate && reminder.status !== 'pending'"
            plain
            :icon="RefreshLeft"
            :loading="saving"
            @click="emit('reopen')"
          >
            重新打开
          </el-button>
          <el-button
            v-if="canMutate"
            type="danger"
            plain
            :icon="Delete"
            :loading="saving"
            @click="emit('archive')"
          >
            归档
          </el-button>
        </div>

        <el-alert
          v-if="reminder.source_type === 'loan_return'"
          class="loan-note"
          type="info"
          :closable="false"
          show-icon
          title="借出归还提醒的归还日期由借用流程维护，请在借用记录中调整。"
        />

        <div class="summary-strip">
          <div>
            <span>到期状态</span>
            <el-tag :type="dueStateTagType(reminder.due_state)" effect="plain">
              {{ dueStateLabel(reminder.due_state) }}
            </el-tag>
          </div>
          <div>
            <span>优先级</span>
            <el-tag :type="priorityTagType(reminder.priority)" effect="plain">
              {{ priorityLabel(reminder.priority) }}
            </el-tag>
          </div>
          <div>
            <span>来源</span>
            <strong>{{ sourceLabel(reminder.source_type) }}</strong>
          </div>
        </div>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="标题">{{ reminder.title }}</el-descriptions-item>
          <el-descriptions-item label="关联物品">
            {{ reminder.item?.name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="来源">{{ sourceLabel(reminder.source_type) }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            {{ statusLabel(reminder.status) }}
          </el-descriptions-item>
          <el-descriptions-item label="提醒日期">{{ formatReminderDate(reminder.remind_at) }}</el-descriptions-item>
          <el-descriptions-item label="到期日期">{{ formatReminderDate(reminder.due_date) }}</el-descriptions-item>
          <el-descriptions-item label="借用人">
            {{ reminder.loan?.borrower_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="预计归还">
            {{ formatReminderDate(reminder.loan?.expected_return_date) }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDateTime(reminder.updated_at) }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(reminder.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="说明" :span="2">
            {{ reminder.description || '-' }}
          </el-descriptions-item>
        </el-descriptions>
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
  min-height: 260px;
}

.action-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.loan-note {
  margin-bottom: 12px;
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.summary-strip > div {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  background: #f8fbf6;
  border: 1px solid #e2e8df;
  border-radius: 8px;
}

.summary-strip span {
  color: #6a756d;
  font-size: 12px;
}

.summary-strip strong {
  color: #25342d;
  font-size: 13px;
}

@media (max-width: 720px) {
  .summary-strip {
    grid-template-columns: 1fr;
  }
}
</style>
