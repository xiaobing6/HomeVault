<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Check, Download, Upload } from '@element-plus/icons-vue'
import { ElMessage, type UploadFile, type UploadInstance } from 'element-plus'

import { getChineseErrorMessage } from '../../api/client'
import type { ImportFieldMessage, ImportPreviewResponse, ImportRowPreview } from '../../api/inventory'
import { useInventoryStore } from '../../stores/inventory'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  imported: [count: number]
  'download-template': []
}>()

const inventory = useInventoryStore()
const uploadRef = ref<UploadInstance>()
const preview = ref<ImportPreviewResponse | null>(null)
const selectedFileName = ref('')
const previewing = ref(false)
const confirming = ref(false)

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value)
})

const canConfirm = computed(() => {
  if (!preview.value?.token) return false
  return preview.value.total_count > 0 && preview.value.invalid_count === 0
})

watch(
  () => props.modelValue,
  (isOpen) => {
    if (!isOpen) resetState()
  }
)

function resetState() {
  preview.value = null
  selectedFileName.value = ''
  previewing.value = false
  confirming.value = false
  uploadRef.value?.clearFiles()
}

function isCsvFile(file: File): boolean {
  return file.name.toLowerCase().endsWith('.csv') || file.type === 'text/csv'
}

function beforeUpload(file: File) {
  if (!isCsvFile(file)) {
    ElMessage.warning('请选择 CSV 文件')
    return false
  }
  return true
}

async function handleFileChange(uploadFile: UploadFile) {
  const rawFile = uploadFile.raw
  if (!rawFile) return

  if (!isCsvFile(rawFile)) {
    ElMessage.warning('请选择 CSV 文件')
    uploadRef.value?.clearFiles()
    return
  }

  selectedFileName.value = rawFile.name
  preview.value = null
  previewing.value = true
  try {
    preview.value = await inventory.previewInventoryImport(rawFile)
    if (preview.value.invalid_count > 0) {
      ElMessage.warning('预览发现错误，请修正后重新上传')
    } else {
      ElMessage.success('预览通过，可以确认导入')
    }
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
    uploadRef.value?.clearFiles()
    selectedFileName.value = ''
  } finally {
    previewing.value = false
  }
}

async function confirmImport() {
  if (!preview.value?.token || !canConfirm.value) return

  confirming.value = true
  try {
    const response = await inventory.confirmInventoryImport({ token: preview.value.token })
    ElMessage.success(`已导入 ${response.imported_count} 个物品`)
    emit('imported', response.imported_count)
    dialogVisible.value = false
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    confirming.value = false
  }
}

function messageText(messages: ImportFieldMessage[]): string {
  if (messages.length === 0) return '-'
  return messages
    .map((message) => (message.field ? `${message.field}: ${message.message}` : message.message))
    .join('；')
}

function originalValue(row: ImportRowPreview, key: string): string {
  return row.original[key] || '-'
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="导入物品"
    width="min(880px, calc(100vw - 32px))"
    destroy-on-close
  >
    <div class="import-dialog">
      <div class="import-actions">
        <el-button :icon="Download" @click="emit('download-template')">
          下载模板
        </el-button>
        <el-upload
          ref="uploadRef"
          accept=".csv,text/csv"
          :auto-upload="false"
          :before-upload="beforeUpload"
          :show-file-list="false"
          :on-change="handleFileChange"
        >
          <el-button type="primary" :icon="Upload" :loading="previewing">
            选择 CSV
          </el-button>
        </el-upload>
      </div>

      <div v-if="selectedFileName" class="selected-file">
        {{ selectedFileName }}
      </div>

      <el-alert
        v-if="preview"
        :closable="false"
        show-icon
        :type="preview.invalid_count > 0 ? 'error' : 'success'"
      >
        <template #title>
          共 {{ preview.total_count }} 行，{{ preview.valid_count }} 行可导入，{{ preview.invalid_count }} 行需修正
        </template>
      </el-alert>

      <el-table
        v-if="preview"
        class="preview-table"
        :data="preview.rows"
        height="360"
        stripe
      >
        <el-table-column prop="row_number" label="行号" width="76" />
        <el-table-column label="名称" min-width="130">
          <template #default="{ row }">
            {{ originalValue(row, 'name') }}
          </template>
        </el-table-column>
        <el-table-column label="分类" min-width="110">
          <template #default="{ row }">
            {{ originalValue(row, 'category') }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="96">
          <template #default="{ row }">
            <el-tag :type="row.is_valid ? 'success' : 'danger'" size="small">
              {{ row.is_valid ? '可导入' : '需修正' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="错误" min-width="220">
          <template #default="{ row }">
            <span class="message-list message-list--error">{{ messageText(row.errors) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="提醒" min-width="200">
          <template #default="{ row }">
            <span class="message-list">{{ messageText(row.warnings) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-else description="请选择模板 CSV 文件" :image-size="72" />
    </div>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button
        type="primary"
        :icon="Check"
        :disabled="!canConfirm"
        :loading="confirming"
        @click="confirmImport"
      >
        确认导入
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.import-dialog {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.import-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.selected-file {
  min-width: 0;
  overflow: hidden;
  color: #536158;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-table {
  width: 100%;
}

.message-list {
  color: #536158;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
}

.message-list--error {
  color: #b42318;
}

@media (max-width: 640px) {
  .import-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .import-actions :deep(.el-button),
  .import-actions :deep(.el-upload) {
    width: 100%;
  }
}
</style>
