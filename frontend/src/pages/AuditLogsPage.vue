<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { DocumentChecked, Refresh, Search, View } from '@element-plus/icons-vue'

import type { AuditLogEntry, AuditLogFilters } from '../api/audit'
import { getChineseErrorMessage } from '../api/client'
import { useAuditLogsStore } from '../stores/auditLogs'

const auditLogs = useAuditLogsStore()
const { logs, selectedLog, total, page, pageSize, loading } = storeToRefs(auditLogs)

const detailDialogOpen = ref(false)

const actionOptions = [
  'auth.login',
  'auth.logout',
  'admin.user.create',
  'admin.user.update',
  'admin.user.reset_password',
  'config.residence.create',
  'config.residence.update',
  'config.location.create',
  'config.family_member.create',
  'config.category.create',
  'config.attribute_definition.create'
]

const resourceTypeOptions = [
  'auth_session',
  'user',
  'residence',
  'location_node',
  'family_member',
  'category',
  'attribute_definition'
]

const searchValue = computed({
  get: () => auditLogs.filters.search ?? '',
  set: (value: string) => {
    auditLogs.applyFilters({ search: value.trim() || null })
  }
})

const actionValue = computed({
  get: () => auditLogs.filters.action ?? '',
  set: (value: string) => {
    void applyAndLoad({ action: value || null })
  }
})

const resourceTypeValue = computed({
  get: () => auditLogs.filters.resource_type ?? '',
  set: (value: string) => {
    void applyAndLoad({ resource_type: value || null })
  }
})

const resultValue = computed({
  get: () => auditLogs.filters.result ?? '',
  set: (value: string) => {
    void applyAndLoad({ result: value || null })
  }
})

const metadataText = computed(() => {
  if (!selectedLog.value?.metadata) return '{}'
  return JSON.stringify(selectedLog.value.metadata, null, 2)
})

onMounted(async () => {
  try {
    await auditLogs.loadLogs()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
})

async function applyAndLoad(filters: AuditLogFilters) {
  try {
    auditLogs.applyFilters(filters)
    await auditLogs.loadLogs()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function refreshSearch() {
  await applyAndLoad({ search: searchValue.value.trim() || null })
}

async function resetFilters() {
  try {
    auditLogs.resetFilters()
    await auditLogs.loadLogs()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function refreshLogs() {
  try {
    await auditLogs.loadLogs()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function changePage(nextPage: number) {
  try {
    auditLogs.setPage(nextPage)
    await auditLogs.loadLogs()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function changePageSize(nextSize: number) {
  try {
    auditLogs.setPageSize(nextSize)
    await auditLogs.loadLogs()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function openLogDetail(logId: number) {
  try {
    const detailLoaded = await auditLogs.openDetail(logId)
    if (!detailLoaded) return
    detailDialogOpen.value = true
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

function closeLogDetail() {
  auditLogs.closeDetail()
}

function formatDateTime(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function resultLabel(value: string): string {
  if (value === 'success') return '成功'
  if (value === 'failure') return '失败'
  return value || '-'
}

function resultTagType(value: string): 'success' | 'danger' | 'info' {
  if (value === 'success') return 'success'
  if (value === 'failure') return 'danger'
  return 'info'
}

function actorLabel(log: AuditLogEntry): string {
  if (log.actor_username) return log.actor_username
  if (log.actor_user_id) return `用户 #${log.actor_user_id}`
  return '系统'
}

function resourceLabel(log: AuditLogEntry): string {
  const label = log.resource_label || log.resource_id
  return label ? `${log.resource_type} / ${label}` : log.resource_type
}
</script>

<template>
  <section class="audit-logs-page">
    <div class="page-heading">
      <div>
        <h1 class="page-title">操作日志</h1>
        <p>查看登录、账号管理和核心配置变更记录</p>
      </div>
      <el-button :icon="Refresh" @click="refreshLogs">刷新</el-button>
    </div>

    <div class="toolbar-panel">
      <el-input
        v-model="searchValue"
        class="search-input"
        :prefix-icon="Search"
        placeholder="搜索操作者、动作、资源或说明"
        clearable
        @keyup.enter="refreshSearch"
        @clear="refreshSearch"
      />

      <div class="filter-actions">
        <el-select v-model="actionValue" class="filter-select wide" placeholder="动作" filterable clearable>
          <el-option v-for="action in actionOptions" :key="action" :label="action" :value="action" />
        </el-select>
        <el-select v-model="resourceTypeValue" class="filter-select" placeholder="资源" filterable clearable>
          <el-option
            v-for="resourceType in resourceTypeOptions"
            :key="resourceType"
            :label="resourceType"
            :value="resourceType"
          />
        </el-select>
        <el-select v-model="resultValue" class="filter-select compact" placeholder="结果" clearable>
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failure" />
        </el-select>
        <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
      </div>
    </div>

    <div class="table-panel">
      <el-table
        v-loading="loading"
        :data="logs"
        row-key="id"
        empty-text="暂无操作日志"
        @row-dblclick="(row: AuditLogEntry) => openLogDetail(row.id)"
      >
        <el-table-column label="时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.occurred_at) }}</template>
        </el-table-column>
        <el-table-column label="动作" min-width="210" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" :icon="DocumentChecked" @click="openLogDetail(row.id)">
              {{ row.action }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="操作者" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ actorLabel(row) }}</template>
        </el-table-column>
        <el-table-column label="资源" min-width="190" show-overflow-tooltip>
          <template #default="{ row }">{{ resourceLabel(row) }}</template>
        </el-table-column>
        <el-table-column label="结果" width="100">
          <template #default="{ row }">
            <el-tag :type="resultTagType(row.result)" effect="plain">
              {{ resultLabel(row.result) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="View" @click="openLogDetail(row.id)">详情</el-button>
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

    <el-dialog
      v-model="detailDialogOpen"
      title="日志详情"
      width="min(820px, 96vw)"
      destroy-on-close
      @closed="closeLogDetail"
    >
      <div v-loading="loading" class="detail-body">
        <el-empty v-if="!selectedLog" description="暂无日志详情" />

        <template v-else>
          <div class="detail-header">
            <div>
              <strong>{{ selectedLog.action }}</strong>
              <span>{{ formatDateTime(selectedLog.occurred_at) }}</span>
            </div>
            <el-tag :type="resultTagType(selectedLog.result)" effect="plain">
              {{ resultLabel(selectedLog.result) }}
            </el-tag>
          </div>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="操作者">{{ actorLabel(selectedLog) }}</el-descriptions-item>
            <el-descriptions-item label="用户 ID">
              {{ selectedLog.actor_user_id ?? '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="资源类型">{{ selectedLog.resource_type }}</el-descriptions-item>
            <el-descriptions-item label="资源 ID">{{ selectedLog.resource_id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="资源名称" :span="2">
              {{ selectedLog.resource_label || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="元数据" :span="2">
              <pre class="metadata-block">{{ metadataText }}</pre>
            </el-descriptions-item>
          </el-descriptions>
        </template>
      </div>
    </el-dialog>
  </section>
</template>

<style scoped>
.audit-logs-page {
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
  width: 150px;
}

.filter-select.wide {
  width: 220px;
}

.filter-select.compact {
  width: 110px;
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

.detail-body {
  min-height: 260px;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.detail-header strong,
.detail-header span {
  display: block;
}

.detail-header strong {
  color: #25342d;
  font-size: 18px;
  word-break: break-word;
}

.detail-header span {
  margin-top: 4px;
  color: #6c756f;
  font-size: 13px;
}

.metadata-block {
  max-height: 260px;
  margin: 0;
  overflow: auto;
  color: #25342d;
  font-family: ui-monospace, SFMono-Regular, Consolas, 'Liberation Mono', monospace;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 960px) {
  .toolbar-panel,
  .filter-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .search-input,
  .filter-select,
  .filter-select.wide,
  .filter-select.compact {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .page-heading {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
