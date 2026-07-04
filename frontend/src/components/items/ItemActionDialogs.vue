<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { Check, Close } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../../api/client'
import type { LocationNode } from '../../api/configuration'
import type { ItemDetail, ItemLoan } from '../../api/inventory'
import { useConfigurationStore } from '../../stores/configuration'
import { useInventoryStore } from '../../stores/inventory'

type ActionType = 'move' | 'status' | 'borrow' | 'return' | 'quantity' | 'archive' | 'delete'
type QuantityMode = 'new' | 'delta'
type PlacementType = 'location' | 'container'

interface OptionItem {
  label: string
  value: number
}

const EXIT_STATUS_SEMANTICS = new Set(['removed', 'missing', 'consumed', 'retired', 'lost', 'disposed'])

const props = defineProps<{
  modelValue: boolean
  action: ActionType | null
  item: ItemDetail | null
  returnLoan?: ItemLoan | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  success: [detail: ItemDetail]
}>()

const configuration = useConfigurationStore()
const inventory = useInventoryStore()
const { data } = storeToRefs(configuration)
const { containerItems, containersLoading } = storeToRefs(inventory)

const saving = ref(false)
const movePlacementType = ref<PlacementType>('location')
const returnPlacementType = ref<PlacementType>('location')

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

const borrowForm = reactive({
  borrower_name: '',
  borrower_contact: '',
  expected_return_date: '',
  loan_note: ''
})

const returnForm = reactive({
  location_node_id: null as number | null,
  container_item_id: null as number | null,
  target_status_id: null as number | null,
  return_note: ''
})

const quantityForm = reactive({
  mode: 'new' as QuantityMode,
  new_quantity: null as number | null,
  delta: null as number | null,
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
  if (props.action === 'move') return '移动物品'
  if (props.action === 'status') return '修改状态'
  if (props.action === 'borrow') return '借出物品'
  if (props.action === 'return') return '归还物品'
  if (props.action === 'quantity') return '调整数量'
  if (props.action === 'archive') return '归档物品'
  if (props.action === 'delete') return '删除物品'
  return '操作物品'
})

const activeStatuses = computed(() =>
  [...(data.value?.item_statuses ?? [])]
    .filter((status) => status.is_active)
    .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
)

const returnStatusOptions = computed(() =>
  activeStatuses.value.filter(
    (status) => status.code !== 'loaned' && !['away', 'loaned'].includes(status.semantic)
  )
)

const defaultReturnStatus = computed(
  () => returnStatusOptions.value.find((status) => status.code === 'in_stock') ?? returnStatusOptions.value[0]
)

const selectedReturnStatus = computed(() =>
  returnStatusOptions.value.find((status) => status.id === returnForm.target_status_id) ?? null
)

const returnUsesExitStatus = computed(() =>
  EXIT_STATUS_SEMANTICS.has(selectedReturnStatus.value?.semantic ?? '')
)

const activeLoan = computed(() => {
  if (props.returnLoan && !props.returnLoan.returned_at) return props.returnLoan
  return (props.item?.loans ?? [])
    .filter((loan) => !loan.returned_at)
    .sort((left, right) =>
      new Date(right.loaned_at).getTime() - new Date(left.loaned_at).getTime() || right.id - left.id
    )[0] ?? null
})

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
  const currentItemId = props.item?.id
  const options = containerItems.value
    .filter((item) => item.is_container && !item.is_archived && item.id !== currentItemId)
    .map((item) => ({ label: item.name, value: item.id }))
  const currentContainerId = props.item?.container_item_id
  const hasCurrentContainer = options.some((option) => option.value === currentContainerId)
  if (currentContainerId && props.item?.container_item_name && !hasCurrentContainer) {
    options.unshift({ label: props.item.container_item_name, value: currentContainerId })
  }
  return options
})

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    resetForms()
    void loadContainerOptions()
  }
)

watch(
  () => props.action,
  () => {
    if (!props.modelValue) return
    resetForms()
    void loadContainerOptions()
  }
)

watch(
  () => props.item,
  () => {
    if (!props.modelValue) return
    resetForms()
    void loadContainerOptions()
  }
)

watch(movePlacementType, (type) => {
  if (type === 'location') moveForm.container_item_id = null
  if (type === 'container') moveForm.location_node_id = null
})

watch(returnPlacementType, (type) => {
  if (type === 'location') returnForm.container_item_id = null
  if (type === 'container') returnForm.location_node_id = null
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

watch(
  () => returnForm.location_node_id,
  (locationNodeId) => {
    if (locationNodeId != null) returnForm.container_item_id = null
  }
)

watch(
  () => returnForm.container_item_id,
  (containerItemId) => {
    if (containerItemId != null) returnForm.location_node_id = null
  }
)

watch(returnUsesExitStatus, (isExitStatus) => {
  if (!isExitStatus) return
  returnForm.location_node_id = null
  returnForm.container_item_id = null
})

function resetForms() {
  const item = props.item
  movePlacementType.value = item?.container_item_id ? 'container' : 'location'
  Object.assign(moveForm, {
    location_node_id: item?.location_node_id ?? null,
    container_item_id: item?.container_item_id ?? null,
    reason: '',
    note: ''
  })

  Object.assign(statusForm, {
    status_id: item?.status_id ?? activeStatuses.value[0]?.id ?? null,
    reason: '',
    note: ''
  })

  Object.assign(borrowForm, {
    borrower_name: '',
    borrower_contact: '',
    expected_return_date: '',
    loan_note: ''
  })

  returnPlacementType.value = item?.container_item_id ? 'container' : 'location'
  Object.assign(returnForm, {
    location_node_id: item?.location_node_id ?? null,
    container_item_id: item?.container_item_id ?? null,
    target_status_id: defaultReturnStatus.value?.id ?? null,
    return_note: ''
  })

  Object.assign(quantityForm, {
    mode: 'new' as QuantityMode,
    new_quantity: item ? Number(item.quantity) : null,
    delta: null,
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
  if (!props.item) {
    ElMessage.warning('请先选择物品')
    return false
  }
  if (props.action === 'move') {
    if (EXIT_STATUS_SEMANTICS.has(props.item.status_semantic)) {
      ElMessage.warning('当前状态不能移动')
      return false
    }
    return validatePlacement(moveForm.location_node_id, moveForm.container_item_id)
  }
  if (props.action === 'status') {
    if (!statusForm.status_id) {
      ElMessage.warning('请选择状态')
      return false
    }
    return true
  }
  if (props.action === 'borrow') {
    if (EXIT_STATUS_SEMANTICS.has(props.item.status_semantic)) {
      ElMessage.warning('当前状态不能借出')
      return false
    }
    if (!borrowForm.borrower_name.trim()) {
      ElMessage.warning('请输入借用人')
      return false
    }
    return true
  }
  if (props.action === 'return') {
    if (!activeLoan.value) {
      ElMessage.warning('没有可归还的借用记录')
      return false
    }
    if (!returnForm.target_status_id) {
      ElMessage.warning('请选择归还后的状态')
      return false
    }
    if (returnUsesExitStatus.value) return true
    return validatePlacement(returnForm.location_node_id, returnForm.container_item_id)
  }
  if (props.action === 'quantity') {
    if (!quantityForm.reason.trim()) {
      ElMessage.warning('请输入调整原因')
      return false
    }
    if (quantityForm.mode === 'new' && quantityForm.new_quantity == null) {
      ElMessage.warning('请输入新数量')
      return false
    }
    if (quantityForm.mode === 'delta' && quantityForm.delta == null) {
      ElMessage.warning('请输入增减数量')
      return false
    }
  }
  return true
}

async function submitAction() {
  if (!props.item || !props.action || !validateSubmit()) return

  saving.value = true
  try {
    let detail: ItemDetail
    if (props.action === 'move') {
      detail = await inventory.moveItem(props.item.id, {
        location_node_id: moveForm.location_node_id,
        container_item_id: moveForm.container_item_id,
        reason: moveForm.reason.trim(),
        note: moveForm.note.trim()
      })
      ElMessage.success('已移动')
    } else if (props.action === 'status') {
      detail = await inventory.changeStatus(props.item.id, {
        status_id: statusForm.status_id as number,
        reason: statusForm.reason.trim(),
        note: statusForm.note.trim()
      })
      ElMessage.success('状态已更新')
    } else if (props.action === 'borrow') {
      detail = await inventory.borrowItem(props.item.id, {
        borrower_name: borrowForm.borrower_name.trim(),
        borrower_contact: borrowForm.borrower_contact.trim(),
        expected_return_date: borrowForm.expected_return_date || null,
        loan_note: borrowForm.loan_note.trim()
      })
      ElMessage.success('已借出')
    } else if (props.action === 'return') {
      detail = await inventory.returnLoan(props.item.id, activeLoan.value!.id, {
        location_node_id: returnUsesExitStatus.value ? null : returnForm.location_node_id,
        container_item_id: returnUsesExitStatus.value ? null : returnForm.container_item_id,
        target_status_id: returnForm.target_status_id,
        return_note: returnForm.return_note.trim()
      })
      ElMessage.success('已归还')
    } else if (props.action === 'quantity') {
      detail = await inventory.adjustQuantity(props.item.id, {
        new_quantity: quantityForm.mode === 'new' ? quantityForm.new_quantity : null,
        delta: quantityForm.mode === 'delta' ? quantityForm.delta : null,
        reason: quantityForm.reason.trim(),
        note: quantityForm.note.trim()
      })
      ElMessage.success('数量已更新')
    } else if (props.action === 'delete') {
      detail = await inventory.deleteItem(props.item.id, {
        delete_reason: deleteForm.delete_reason.trim()
      })
      ElMessage.success('已删除')
    } else {
      detail = await inventory.archiveItem(props.item.id, {
        archive_reason: archiveForm.archive_reason.trim()
      })
      ElMessage.success('已归档')
    }

    emit('success', detail)
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
    <el-form label-position="top" class="action-form">
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
          <el-input v-model="moveForm.reason" maxlength="255" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="moveForm.note" type="textarea" :rows="3" maxlength="500" />
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
          <el-input v-model="statusForm.reason" maxlength="255" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="statusForm.note" type="textarea" :rows="3" maxlength="500" />
        </el-form-item>
      </template>

      <template v-else-if="action === 'borrow'">
        <el-form-item label="借用人" required>
          <el-input v-model="borrowForm.borrower_name" maxlength="160" clearable />
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-model="borrowForm.borrower_contact" maxlength="160" clearable />
        </el-form-item>
        <el-form-item label="预计归还日期">
          <el-date-picker
            v-model="borrowForm.expected_return_date"
            class="full-width"
            type="date"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="borrowForm.loan_note" type="textarea" :rows="3" maxlength="500" />
        </el-form-item>
      </template>

      <template v-else-if="action === 'return'">
        <el-alert
          v-if="activeLoan"
          :title="`借用人：${activeLoan.borrower_name}`"
          type="info"
          :closable="false"
        />
        <el-form-item label="归还后状态" required>
          <el-select v-model="returnForm.target_status_id" class="full-width" filterable>
            <el-option
              v-for="status in returnStatusOptions"
              :key="status.id"
              :label="status.name"
              :value="status.id"
            />
          </el-select>
        </el-form-item>

        <el-alert
          v-if="returnUsesExitStatus"
          title="该状态不需要设置位置或容器"
          type="info"
          :closable="false"
        />
        <template v-else>
          <el-radio-group v-model="returnPlacementType" class="placement-tabs">
            <el-radio-button label="location">放在位置</el-radio-button>
            <el-radio-button label="container">放入容器</el-radio-button>
          </el-radio-group>
          <el-form-item v-if="returnPlacementType === 'location'" label="位置" required>
            <el-select
              v-model="returnForm.location_node_id"
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
              v-model="returnForm.container_item_id"
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
        </template>

        <el-form-item label="归还备注">
          <el-input v-model="returnForm.return_note" type="textarea" :rows="3" maxlength="500" />
        </el-form-item>
      </template>

      <template v-else-if="action === 'quantity'">
        <el-form-item label="调整方式" required>
          <el-radio-group v-model="quantityForm.mode">
            <el-radio-button label="new">新数量</el-radio-button>
            <el-radio-button label="delta">增减数量</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="quantityForm.mode === 'new'" label="新数量" required>
          <el-input-number
            v-model="quantityForm.new_quantity"
            class="full-width"
            :precision="2"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item v-else label="增减数量" required>
          <el-input-number
            v-model="quantityForm.delta"
            class="full-width"
            :precision="2"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item label="原因" required>
          <el-input v-model="quantityForm.reason" maxlength="255" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="quantityForm.note" type="textarea" :rows="3" maxlength="500" />
        </el-form-item>
      </template>

      <template v-else-if="action === 'archive'">
        <el-form-item label="归档原因">
          <el-input
            v-model="archiveForm.archive_reason"
            type="textarea"
            :rows="4"
            maxlength="255"
            show-word-limit
          />
        </el-form-item>
      </template>

      <template v-else-if="action === 'delete'">
        <el-alert
          title="删除后，物品将从普通列表、导出和详情入口隐藏。"
          type="warning"
          :closable="false"
        />
        <el-form-item label="删除原因">
          <el-input
            v-model="deleteForm.delete_reason"
            type="textarea"
            :rows="4"
            maxlength="255"
            show-word-limit
          />
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button :icon="Close" @click="emit('update:modelValue', false)">取消</el-button>
        <el-button type="primary" :icon="Check" :loading="saving" @click="submitAction">
          确认
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.action-form {
  display: grid;
  gap: 8px;
}

.full-width {
  width: 100%;
}

.placement-tabs {
  margin-bottom: 8px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 560px) {
  .dialog-footer {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
