<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Bell, Plus, Refresh, Search } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../api/client'
import type {
  ReminderCreateRequest,
  ReminderDetail,
  ReminderDueState,
  ReminderFilters,
  ReminderPriority,
  ReminderSourceType,
  ReminderStatus,
  ReminderSummary,
  ReminderUpdateRequest
} from '../api/reminders'
import ReminderDetailModal from '../components/reminders/ReminderDetailModal.vue'
import ReminderFormDialog from '../components/reminders/ReminderFormDialog.vue'
import { useAuthStore } from '../stores/auth'
import { useReminderStore } from '../stores/reminders'
import { formatReminderDate } from '../utils/reminderDates'

const auth = useAuthStore()
const reminders = useReminderStore()
const { loading, saving, selectedReminder, total, page, pageSize } = storeToRefs(reminders)

const detailOpen = ref(false)
const formOpen = ref(false)
const editingReminder = ref<ReminderDetail | null>(null)

const canEdit = computed(() => auth.hasPermission('items:edit'))
const rows = computed(() => reminders.reminders)

const searchValue = computed({
  get: () => reminders.filters.search ?? '',
  set: (value: string) => {
    reminders.applyFilters({ search: value.trim() || null })
  }
})

const statusValue = computed({
  get: () => reminders.filters.status ?? '',
  set: (value: ReminderStatus | '') => {
    void applyAndLoad({ status: value || null })
  }
})

const sourceValue = computed({
  get: () => reminders.filters.source_type ?? '',
  set: (value: ReminderSourceType | '') => {
    void applyAndLoad({ source_type: value || null })
  }
})

const upcomingValue = computed({
  get: () => {
    if (reminders.filters.overdue) return 'overdue'
    if (typeof reminders.filters.upcoming_days === 'number') return String(reminders.filters.upcoming_days)
    return ''
  },
  set: (value: string) => {
    if (value === 'overdue') {
      void applyAndLoad({ overdue: true, upcoming_days: null })
      return
    }
    void applyAndLoad({
      overdue: null,
      upcoming_days: value ? Number(value) : null
    })
  }
})

const counters = computed(() => {
  const initial = { overdue: 0, upcoming: 0, pending: 0, done: 0, dismissed: 0 }
  return rows.value.reduce((accumulator, reminder) => {
    if (reminder.due_state === 'overdue') accumulator.overdue += 1
    if (reminder.due_state === 'upcoming') accumulator.upcoming += 1
    if (reminder.status === 'pending') accumulator.pending += 1
    if (reminder.status === 'done') accumulator.done += 1
    if (reminder.status === 'dismissed') accumulator.dismissed += 1
    return accumulator
  }, initial)
})

onMounted(async () => {
  try {
    await reminders.loadReminders()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
})

async function applyAndLoad(filters: ReminderFilters) {
  try {
    reminders.applyFilters(filters)
    await reminders.loadReminders()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function refreshSearch() {
  await applyAndLoad({ search: searchValue.value.trim() || null })
}

async function resetFilters() {
  try {
    reminders.resetFilters()
    await reminders.loadReminders()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function changePage(nextPage: number) {
  try {
    reminders.setPage(nextPage)
    await reminders.loadReminders()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function changePageSize(nextSize: number) {
  try {
    reminders.setPageSize(nextSize)
    await reminders.loadReminders()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function openDetail(reminderId: number) {
  try {
    await reminders.openDetail(reminderId)
    detailOpen.value = true
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

function openCreateDialog() {
  if (!canEdit.value) return
  editingReminder.value = null
  formOpen.value = true
}

function openEditDialog() {
  if (!selectedReminder.value || !canEdit.value) return
  editingReminder.value = selectedReminder.value
  formOpen.value = true
}

async function saveReminder(payload: ReminderCreateRequest | ReminderUpdateRequest) {
  try {
    const saved = editingReminder.value
      ? await reminders.updateReminder(editingReminder.value.id, payload as ReminderUpdateRequest)
      : await reminders.createReminder(payload as ReminderCreateRequest)
    editingReminder.value = null
    formOpen.value = false
    detailOpen.value = true
    await reminders.openDetail(saved.id)
    ElMessage.success('提醒已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function runLifecycleAction(
  action: 'complete' | 'dismiss' | 'reopen' | 'archive',
  successMessage: string
) {
  const reminder = selectedReminder.value
  if (!reminder || !canEdit.value) return

  try {
    if (action === 'archive') {
      await ElMessageBox.confirm('归档后该提醒将从默认列表中隐藏，确认继续吗？', '归档提醒', {
        type: 'warning',
        confirmButtonText: '归档',
        cancelButtonText: '取消'
      })
    }

    if (action === 'complete') await reminders.completeReminder(reminder.id)
    if (action === 'dismiss') await reminders.dismissReminder(reminder.id)
    if (action === 'reopen') await reminders.reopenReminder(reminder.id)
    if (action === 'archive') await reminders.archiveReminder(reminder.id)

    ElMessage.success(successMessage)
  } catch (error) {
    if (error === 'cancel') return
    ElMessage.error(getChineseErrorMessage(error))
  }
}

function closeDetail() {
  detailOpen.value = false
  reminders.closeDetail()
}

function sourceLabel(value: ReminderSourceType): string {
  if (value === 'loan_return') return '借出归还'
  return '手动提醒'
}

function statusLabel(value: ReminderStatus): string {
  if (value === 'pending') return '待处理'
  if (value === 'done') return '已完成'
  return '已忽略'
}

function statusTagType(value: ReminderStatus): 'success' | 'warning' | 'info' {
  if (value === 'done') return 'success'
  if (value === 'pending') return 'warning'
  return 'info'
}

function dueStateLabel(value: ReminderDueState): string {
  if (value === 'overdue') return '已逾期'
  if (value === 'upcoming') return '即将到期'
  if (value === 'scheduled') return '已安排'
  if (value === 'done') return '已完成'
  if (value === 'dismissed') return '已忽略'
  if (value === 'none') return '无日期'
  return '待处理'
}

function dueStateTagType(value: ReminderDueState): 'danger' | 'warning' | 'success' | 'info' {
  if (value === 'overdue') return 'danger'
  if (value === 'upcoming' || value === 'pending') return 'warning'
  if (value === 'done') return 'success'
  return 'info'
}

function priorityLabel(value: ReminderPriority): string {
  if (value === 'high') return '高'
  if (value === 'low') return '低'
  return '普通'
}

function priorityTagType(value: ReminderPriority): 'danger' | 'warning' | 'info' {
  if (value === 'high') return 'danger'
  if (value === 'low') return 'info'
  return 'warning'
}

function formatDateTime(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function itemName(row: ReminderSummary): string {
  return row.item?.name || '-'
}
</script>

<template>
  <section class="reminders-page">
    <div class="page-heading">
      <div>
        <h1 class="page-title">提醒中心</h1>
        <p>集中查看手动提醒和借出归还提醒</p>
      </div>
      <el-button v-if="canEdit" type="primary" :icon="Plus" @click="openCreateDialog">
        新增提醒
      </el-button>
    </div>

    <div class="counter-row">
      <div class="counter">
        <span>已逾期</span>
        <strong>{{ counters.overdue }}</strong>
      </div>
      <div class="counter">
        <span>即将到期</span>
        <strong>{{ counters.upcoming }}</strong>
      </div>
      <div class="counter">
        <span>待处理</span>
        <strong>{{ counters.pending }}</strong>
      </div>
      <div class="counter">
        <span>已完成</span>
        <strong>{{ counters.done }}</strong>
      </div>
      <div class="counter">
        <span>已忽略</span>
        <strong>{{ counters.dismissed }}</strong>
      </div>
    </div>

    <div class="toolbar-panel">
      <el-input
        v-model="searchValue"
        class="search-input"
        :prefix-icon="Search"
        placeholder="搜索提醒标题或说明"
        clearable
        @keyup.enter="refreshSearch"
        @clear="refreshSearch"
      />

      <div class="filter-actions">
        <el-select v-model="statusValue" class="filter-select" placeholder="状态" clearable>
          <el-option label="待处理" value="pending" />
          <el-option label="已完成" value="done" />
          <el-option label="已忽略" value="dismissed" />
        </el-select>
        <el-select v-model="sourceValue" class="filter-select" placeholder="来源" clearable>
          <el-option label="手动提醒" value="manual" />
          <el-option label="借出归还" value="loan_return" />
        </el-select>
        <el-select v-model="upcomingValue" class="filter-select" placeholder="时间窗口" clearable>
          <el-option label="已逾期" value="overdue" />
          <el-option label="未来 7 天" value="7" />
          <el-option label="未来 30 天" value="30" />
          <el-option label="未来 90 天" value="90" />
        </el-select>
        <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
      </div>
    </div>

    <div class="table-panel">
      <el-table
        v-loading="loading"
        :data="rows"
        row-key="id"
        empty-text="暂无提醒"
        @row-dblclick="(row: ReminderSummary) => openDetail(row.id)"
      >
        <el-table-column label="标题" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" :icon="Bell" @click="openDetail(row.id)">
              {{ row.title }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="物品" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ itemName(row) }}</template>
        </el-table-column>
        <el-table-column label="来源" width="110">
          <template #default="{ row }">{{ sourceLabel(row.source_type) }}</template>
        </el-table-column>
        <el-table-column label="到期状态" width="120">
          <template #default="{ row }">
            <el-tag :type="dueStateTagType(row.due_state)" effect="plain">
              {{ dueStateLabel(row.due_state) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="到期日期" width="130">
          <template #default="{ row }">{{ formatReminderDate(row.due_date) }}</template>
        </el-table-column>
        <el-table-column label="优先级" width="100">
          <template #default="{ row }">
            <el-tag :type="priorityTagType(row.priority)" effect="plain">
              {{ priorityLabel(row.priority) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="105">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" effect="plain">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row.id)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pagination-row">
      <el-pagination
        background
        layout="total, sizes, prev, pager, next"
        :total="total"
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[20, 40, 80]"
        @current-change="changePage"
        @size-change="changePageSize"
      />
    </div>

    <ReminderDetailModal
      v-model="detailOpen"
      :reminder="selectedReminder"
      :loading="loading"
      :saving="saving"
      :can-edit="canEdit"
      @edit="openEditDialog"
      @complete="runLifecycleAction('complete', '提醒已完成')"
      @dismiss="runLifecycleAction('dismiss', '提醒已忽略')"
      @reopen="runLifecycleAction('reopen', '提醒已重新打开')"
      @archive="runLifecycleAction('archive', '提醒已归档')"
      @close="closeDetail"
    />

    <ReminderFormDialog
      v-model="formOpen"
      :reminder="editingReminder"
      :saving="saving"
      @submit="saveReminder"
    />
  </section>
</template>

<style scoped>
.reminders-page {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.page-heading p {
  margin: 4px 0 0;
  color: #69766d;
}

.counter-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.counter {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-width: 0;
  padding: 12px 14px;
  background: #fff;
  border: 1px solid #e2e8df;
  border-radius: 8px;
}

.counter span {
  color: #6f7a72;
  font-size: 13px;
}

.counter strong {
  color: #25342d;
  font-size: 20px;
}

.toolbar-panel,
.pagination-row,
.table-panel {
  min-width: 0;
  background: #fff;
  border: 1px solid #e2e8df;
  border-radius: 8px;
}

.toolbar-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
}

.search-input {
  width: min(360px, 100%);
}

.filter-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  min-width: 0;
}

.filter-select {
  width: 132px;
}

.table-panel {
  overflow: hidden;
}

.pagination-row {
  display: flex;
  justify-content: flex-end;
  padding: 12px;
  overflow-x: auto;
}

@media (max-width: 960px) {
  .counter-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .toolbar-panel,
  .filter-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .search-input,
  .filter-select {
    width: 100%;
  }
}

@media (max-width: 560px) {
  .page-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .counter-row {
    grid-template-columns: 1fr;
  }
}
</style>
