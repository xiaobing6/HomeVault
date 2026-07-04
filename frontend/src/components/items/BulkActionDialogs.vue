<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { Check, Close } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../../api/client'
import type { LocationNode } from '../../api/configuration'
import type { BulkItemOperationResponse } from '../../api/inventory'
import { useConfigurationStore } from '../../stores/configuration'
import { useInventoryStore } from '../../stores/inventory'

type BulkActionType = 'move' | 'status' | 'archive' | 'delete'
type PlacementType = 'location' | 'container'

interface OptionItem {
  label: string
  value: number
}

const props = defineProps<{
  modelValue: boolean
  action: BulkActionType | null
  selectedItemIds: number[]
  selectedCount: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  success: [response: BulkItemOperationResponse]
}>()

const configuration = useConfigurationStore()
const inventory = useInventoryStore()
const { data } = storeToRefs(configuration)
const { containerItems, containersLoading } = storeToRefs(inventory)

const saving = ref(false)
const movePlacementType = ref<PlacementType>('location')

const moveForm = reactive({
  location_node_id: null as number | null,
  container_item_id: null as number | null,
  reason: '',
  note: ''
})

const statusForm = reactive({
  status_id: null as number | null,
  reason: '',
  note: ''
})

const archiveForm = reactive({
  archive_reason: ''
})

const deleteForm = reactive({
  delete_reason: ''
})

const dialogTitle = computed(() => {
  if (props.action === 'move') return '批量移动'
  if (props.action === 'status') return '批量修改状态'
  if (props.action === 'archive') return '批量归档'
  if (props.action === 'delete') return '批量删除'
  return '批量操作'
})

const activeStatuses = computed(() =>
  [...(data.value?.item_statuses ?? [])]
    .filter((status) => status.is_active)
    .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
)

const locationOptions = computed<OptionItem[]>(() => {
  const residenceNameById = new Map((data.value?.residences ?? []).map((residence) => [
    residence.id,
    residence.name
  ]))
  return (data.value?.location_tree ?? []).flatMap((node) =>
    flattenLocationNodes(node, residenceNameById.get(node.residence_id) ?? '位置')
  )
})

const containerOptions = computed<OptionItem[]>(() => {
  const selectedIds = new Set(props.selectedItemIds)
  return containerItems.value
    .filter((item) => item.is_container && !item.is_archived && !selectedIds.has(item.id))
    .map((item) => ({ label: item.name, value: item.id }))
})

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    resetForms()
    if (props.action === 'move') void loadContainerOptions()
  }
)

watch(
  () => props.action,
  () => {
    if (!props.modelValue) return
    resetForms()
    if (props.action === 'move') void loadContainerOptions()
  }
)

watch(movePlacementType, (type) => {
  if (type === 'location') moveForm.container_item_id = null
  if (type === 'container') moveForm.location_node_id = null
})

watch(
  () => moveForm.location_node_id,
  (locationNodeId) => {
    if (locationNodeId != null) moveForm.container_item_id = null
  }
)

watch(
  () => moveForm.container_item_id,
  (containerItemId) => {
    if (containerItemId != null) moveForm.location_node_id = null
  }
)

function resetForms() {
  movePlacementType.value = 'location'
  Object.assign(moveForm, {
    location_node_id: null,
    container_item_id: null,
    reason: '',
    note: ''
  })
  Object.assign(statusForm, {
    status_id: activeStatuses.value[0]?.id ?? null,
    reason: '',
    note: ''
  })
  archiveForm.archive_reason = ''
  deleteForm.delete_reason = ''
}

function flattenLocationNodes(node: LocationNode, prefix: string): OptionItem[] {
  const label = `${prefix} / ${node.name}`
  const children = [...(node.children ?? [])]
    .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
    .flatMap((child) => flattenLocationNodes(child, label))
  if (!node.is_active) return children
  return [{ label, value: node.id }, ...children]
}

function updateOpen(open: boolean) {
  emit('update:modelValue', open)
}

async function loadContainerOptions() {
  try {
    await inventory.loadContainers()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

function validatePlacement(locationNodeId: number | null, containerItemId: number | null): boolean {
  if (locationNodeId != null && containerItemId != null) {
    ElMessage.warning('位置和容器只能选择一个')
    return false
  }
  if (locationNodeId == null && containerItemId == null) {
    ElMessage.warning('请选择位置或容器')
    return false
  }
  return true
}

function validateSubmit(): boolean {
  if (props.selectedItemIds.length === 0) {
    ElMessage.warning('请先选择物品')
    return false
  }
  if (props.action === 'move') {
    return validatePlacement(moveForm.location_node_id, moveForm.container_item_id)
  }
  if (props.action === 'status' && !statusForm.status_id) {
    ElMessage.warning('请选择状态')
    return false
  }
  return true
}

async function submitAction() {
  if (!props.action || !validateSubmit()) return

  saving.value = true
  try {
    let response: BulkItemOperationResponse
    if (props.action === 'move') {
      response = await inventory.bulkMoveItems({
        item_ids: props.selectedItemIds,
        location_node_id: movePlacementType.value === 'location' ? moveForm.location_node_id : null,
        container_item_id: movePlacementType.value === 'container' ? moveForm.container_item_id : null,
        reason: moveForm.reason.trim(),
        note: moveForm.note.trim()
      })
      ElMessage.success(`已移动 ${response.updated_count} 个物品`)
    } else if (props.action === 'status') {
      response = await inventory.bulkChangeStatus({
        item_ids: props.selectedItemIds,
        status_id: statusForm.status_id as number,
        reason: statusForm.reason.trim(),
        note: statusForm.note.trim()
      })
      ElMessage.success(`已更新 ${response.updated_count} 个物品`)
    } else if (props.action === 'delete') {
      response = await inventory.bulkDeleteItems({
        item_ids: props.selectedItemIds,
        delete_reason: deleteForm.delete_reason.trim()
      })
      ElMessage.success(`已删除 ${response.updated_count} 个物品`)
    } else {
      response = await inventory.bulkArchiveItems({
        item_ids: props.selectedItemIds,
        archive_reason: archiveForm.archive_reason.trim()
      })
      ElMessage.success(`已归档 ${response.updated_count} 个物品`)
    }

    emit('success', response)
    emit('update:modelValue', false)
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="dialogTitle"
    width="min(560px, 94vw)"
    destroy-on-close
    @update:model-value="updateOpen"
  >
    <el-form label-position="top" class="bulk-action-form">
      <p class="selection-summary">已选择 {{ selectedCount }} 个物品</p>

      <template v-if="action === 'move'">
        <el-radio-group v-model="movePlacementType" class="placement-tabs">
          <el-radio-button label="location">放在位置</el-radio-button>
          <el-radio-button label="container">放入容器</el-radio-button>
        </el-radio-group>
        <el-form-item v-if="movePlacementType === 'location'" label="位置" required>
          <el-select
            v-model="moveForm.location_node_id"
            class="full-width"
            clearable
            filterable
          >
            <el-option
              v-for="location in locationOptions"
              :key="location.value"
              :label="location.label"
              :value="location.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-else label="容器" required>
          <el-select
            v-model="moveForm.container_item_id"
            class="full-width"
            clearable
            filterable
            :loading="containersLoading"
          >
            <el-option
              v-for="container in containerOptions"
              :key="container.value"
              :label="container.label"
              :value="container.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="moveForm.reason" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="moveForm.note" type="textarea" :rows="3" />
        </el-form-item>
      </template>

      <template v-else-if="action === 'status'">
        <el-form-item label="状态" required>
          <el-select v-model="statusForm.status_id" class="full-width" filterable>
            <el-option
              v-for="status in activeStatuses"
              :key="status.id"
              :label="status.name"
              :value="status.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="statusForm.reason" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="statusForm.note" type="textarea" :rows="3" />
        </el-form-item>
      </template>

      <template v-else-if="action === 'archive'">
        <el-form-item label="归档原因">
          <el-input v-model="archiveForm.archive_reason" maxlength="255" show-word-limit />
        </el-form-item>
      </template>

      <template v-else-if="action === 'delete'">
        <el-alert
          title="删除后，所选物品将从普通列表、导出和详情入口隐藏。"
          type="warning"
          :closable="false"
        />
        <el-form-item label="删除原因">
          <el-input v-model="deleteForm.delete_reason" maxlength="255" show-word-limit />
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <el-button :icon="Close" @click="updateOpen(false)">取消</el-button>
      <el-button type="primary" :icon="Check" :loading="saving" @click="submitAction">
        确认
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.bulk-action-form {
  display: grid;
  gap: 12px;
}

.selection-summary {
  margin: 0;
  color: #5d6b63;
  font-size: 13px;
}

.placement-tabs {
  margin-bottom: 4px;
}

.full-width {
  width: 100%;
}
</style>
