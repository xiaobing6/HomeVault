<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ArrowRight, Check, Close } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../../api/client'
import type {
  AttributeDefinition,
  Category,
  DictionaryOption,
  LocationNode
} from '../../api/configuration'
import type {
  ItemCreateRequest,
  ItemDetail,
  ItemUpdateRequest
} from '../../api/inventory'
import { useConfigurationStore } from '../../stores/configuration'
import { useInventoryStore } from '../../stores/inventory'
import CustomFieldInputs from './CustomFieldInputs.vue'
import MediaUploader from './MediaUploader.vue'

interface OptionItem {
  label: string
  value: number
}

interface ItemFormModel {
  name: string
  description: string
  category_id: number | null
  status_id: number | null
  quantity: number | null
  unit: string
  owner_member_id: number | null
  keeper_member_id: number | null
  location_node_id: number | null
  container_item_id: number | null
  is_container: boolean
  privacy_level: string
  tagsText: string
}

const EXIT_STATUS_SEMANTICS = new Set(['removed', 'missing', 'consumed'])

const props = defineProps<{
  modelValue: boolean
  item?: ItemDetail | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [detail: ItemDetail]
}>()

const configuration = useConfigurationStore()
const inventory = useInventoryStore()
const { data } = storeToRefs(configuration)

const activeStep = ref(0)
const saving = ref(false)
const placementType = ref<'location' | 'container'>('location')
const imageFiles = ref<File[]>([])
const attachmentFiles = ref<File[]>([])
const attributeValues = ref<Record<number, string>>({})

const form = reactive<ItemFormModel>(createEmptyForm())

const steps = ['分类', '基本信息', '位置或容器', '自定义字段', '图片和附件']
const privacyOptions = [
  { label: '普通', value: 'normal' },
  { label: '私密', value: 'private' },
  { label: '加密', value: 'encrypted' }
]

const isEditing = computed(() => Boolean(props.item?.id))
const drawerTitle = computed(() => (isEditing.value ? '编辑物品' : '新增物品'))
const activeStatuses = computed(() =>
  [...(data.value?.item_statuses ?? [])]
    .filter((status) => status.is_active)
    .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
)
const defaultStatus = computed(
  () => activeStatuses.value.find((status) => status.code === 'in_stock') ?? activeStatuses.value[0]
)
const selectedStatus = computed(() =>
  activeStatuses.value.find((status) => status.id === form.status_id) ?? null
)
const placementStatusSemantic = computed(() =>
  selectedStatus.value?.semantic ?? props.item?.status_semantic ?? ''
)
const isExitPlacementStatus = computed(() =>
  EXIT_STATUS_SEMANTICS.has(placementStatusSemantic.value)
)
const activeMembers = computed(() =>
  [...(data.value?.family_members ?? [])]
    .filter((member) => member.is_active)
    .sort((left, right) => left.id - right.id)
)
const categoryOptions = computed<OptionItem[]>(() =>
  flattenCategories(data.value?.categories ?? [])
)
const selectedCategory = computed(() =>
  form.category_id ? findCategory(data.value?.categories ?? [], form.category_id) : null
)
const selectedDefinitions = computed<AttributeDefinition[]>(() =>
  [...(selectedCategory.value?.attribute_definitions ?? [])]
    .filter((definition) => definition.is_active)
    .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
)
const unitOptions = computed<DictionaryOption[]>(() => {
  const group = data.value?.dictionary_groups.find((item) => item.code === 'units')
  return [...(group?.options ?? [])]
    .filter((option) => option.is_active)
    .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
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
  const options = inventory.items
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
    if (open) resetForm()
  }
)

watch(
  () => props.item,
  () => {
    if (props.modelValue) resetForm()
  }
)

watch(
  () => form.category_id,
  () => {
    applyDefaultAttributeValues()
  }
)

watch(
  placementType,
  (type) => {
    if (type === 'location') {
      form.container_item_id = null
    } else {
      form.location_node_id = null
    }
  }
)

watch(
  () => form.location_node_id,
  (locationNodeId) => {
    if (locationNodeId != null) form.container_item_id = null
  }
)

watch(
  () => form.container_item_id,
  (containerItemId) => {
    if (containerItemId != null) form.location_node_id = null
  }
)

watch(isExitPlacementStatus, (isExitStatus) => {
  if (!isExitStatus) return
  form.location_node_id = null
  form.container_item_id = null
})

function createEmptyForm(): ItemFormModel {
  return {
    name: '',
    description: '',
    category_id: null,
    status_id: null,
    quantity: 1,
    unit: '件',
    owner_member_id: null,
    keeper_member_id: null,
    location_node_id: null,
    container_item_id: null,
    is_container: false,
    privacy_level: 'normal',
    tagsText: ''
  }
}

function resetForm() {
  const item = props.item
  activeStep.value = 0
  imageFiles.value = []
  attachmentFiles.value = []

  if (item) {
    Object.assign(form, {
      name: item.name,
      description: item.description ?? '',
      category_id: item.category_id,
      status_id: item.status_id,
      quantity: Number(item.quantity),
      unit: item.unit || '件',
      owner_member_id: item.owner_member_id,
      keeper_member_id: item.keeper_member_id,
      location_node_id: item.location_node_id,
      container_item_id: item.container_item_id,
      is_container: item.is_container,
      privacy_level: item.privacy_level || 'normal',
      tagsText: item.tags.map((tag) => tag.name).join('\n')
    })
    attributeValues.value = Object.fromEntries(
      item.attribute_values.map((value) => [value.attribute_definition_id, value.value])
    )
    placementType.value = item.container_item_id ? 'container' : 'location'
  } else {
    Object.assign(form, createEmptyForm(), {
      status_id: defaultStatus.value?.id ?? null,
      unit: unitOptions.value[0]?.value || '件'
    })
    attributeValues.value = {}
    placementType.value = 'location'
  }
  applyDefaultAttributeValues()
}

function flattenCategories(nodes: Category[], depth = 0): OptionItem[] {
  const sortedNodes = [...nodes].sort((left, right) =>
    left.sort_order - right.sort_order || left.name.localeCompare(right.name) || left.id - right.id
  )
  return sortedNodes.flatMap((node) => {
    const children = flattenCategories(node.children ?? [], depth + (node.is_active ? 1 : 0))
    if (!node.is_active) return children
    return [
      { label: `${'　'.repeat(depth)}${node.name}`, value: node.id },
      ...children
    ]
  })
}

function findCategory(nodes: Category[], categoryId: number): Category | null {
  for (const node of nodes) {
    if (node.id === categoryId) return node
    const child = findCategory(node.children ?? [], categoryId)
    if (child) return child
  }
  return null
}

function flattenLocationNodes(node: LocationNode, prefix: string): OptionItem[] {
  const label = `${prefix} / ${node.name}`
  const children = [...(node.children ?? [])]
    .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
    .flatMap((child) => flattenLocationNodes(child, label))
  if (!node.is_active) return children
  return [{ label, value: node.id }, ...children]
}

function applyDefaultAttributeValues() {
  const nextValues = { ...attributeValues.value }
  for (const definition of selectedDefinitions.value) {
    if (nextValues[definition.id] != null) continue
    if (definition.default_value) {
      nextValues[definition.id] = definition.default_value
    } else if (definition.field_type === 'boolean') {
      nextValues[definition.id] = 'false'
    }
  }
  attributeValues.value = nextValues
}

function parseTags(): string[] {
  const tags = form.tagsText
    .split(/[\n,，]+/)
    .map((tag) => tag.trim())
    .filter(Boolean)
  return [...new Set(tags)]
}

function validateStep(step: number, requireAttachment = true): boolean {
  if (step === 0) return validateCategory()
  if (step === 1) return validateBasicInfo()
  if (step === 2) return validatePlacement()
  if (step === 3) return validateRequiredAttributes(requireAttachment)
  return true
}

function validateAll(): boolean {
  return [0, 1, 2, 3].every((step) => validateStep(step))
}

function validateCategory(): boolean {
  if (!form.category_id) {
    ElMessage.warning('请选择分类')
    return false
  }
  if (!selectedCategory.value?.is_active) {
    ElMessage.warning('请选择启用中的分类')
    return false
  }
  return true
}

function validateBasicInfo(): boolean {
  if (!form.name.trim()) {
    ElMessage.warning('请输入物品名称')
    return false
  }
  if (!isEditing.value && !form.status_id) {
    ElMessage.warning('请选择状态')
    return false
  }
  if (!form.unit.trim()) {
    ElMessage.warning('请输入单位')
    return false
  }
  if (!isEditing.value && (form.quantity == null || !Number.isFinite(form.quantity))) {
    ElMessage.warning('请输入初始数量')
    return false
  }
  return true
}

function validatePlacement(): boolean {
  const hasLocation = form.location_node_id != null
  const hasContainer = form.container_item_id != null
  if (hasLocation && hasContainer) {
    ElMessage.warning('位置和容器只能选择一个')
    return false
  }
  if (isExitPlacementStatus.value) {
    return true
  }
  if (!hasLocation && !hasContainer) {
    ElMessage.warning('请选择位置或容器')
    return false
  }
  return true
}

function validateRequiredAttributes(requireAttachment: boolean): boolean {
  for (const definition of selectedDefinitions.value) {
    if (!definition.is_required) continue
    if (definition.field_type === 'attachment') {
      if (!requireAttachment || attachmentNames().length > 0) continue
    }
    if ((attributeValues.value[definition.id] ?? '').trim() === '') {
      ElMessage.warning(`请填写${definition.name}`)
      return false
    }
  }
  return true
}

function attachmentNames(): string[] {
  return [
    ...(props.item?.attachments ?? []).map((attachment) => attachment.original_filename),
    ...attachmentFiles.value.map((file) => file.name)
  ].filter(Boolean)
}

function buildAttributeInputs() {
  return selectedDefinitions.value.map((definition) => {
    let value = attributeValues.value[definition.id] ?? ''
    if (definition.field_type === 'attachment' && value.trim() === '') {
      value = attachmentNames().join(',')
    }
    return {
      attribute_definition_id: definition.id,
      value
    }
  })
}

function buildCreatePayload(): ItemCreateRequest {
  return {
    name: form.name.trim(),
    description: form.description.trim(),
    category_id: form.category_id as number,
    status_id: form.status_id as number,
    quantity: form.quantity ?? 1,
    unit: form.unit.trim(),
    owner_member_id: form.owner_member_id,
    keeper_member_id: form.keeper_member_id,
    location_node_id: isExitPlacementStatus.value ? null : form.location_node_id,
    container_item_id: isExitPlacementStatus.value ? null : form.container_item_id,
    is_container: form.is_container,
    privacy_level: form.privacy_level,
    attribute_values: buildAttributeInputs(),
    tags: parseTags()
  }
}

function buildUpdatePayload(): ItemUpdateRequest {
  return {
    name: form.name.trim(),
    description: form.description.trim(),
    category_id: form.category_id as number,
    unit: form.unit.trim(),
    owner_member_id: form.owner_member_id,
    keeper_member_id: form.keeper_member_id,
    is_container: form.is_container,
    privacy_level: form.privacy_level,
    attribute_values: buildAttributeInputs(),
    tags: parseTags()
  }
}

function placementChanged(): boolean {
  if (!props.item || isExitPlacementStatus.value) return false
  return (
    props.item.location_node_id !== form.location_node_id ||
    props.item.container_item_id !== form.container_item_id
  )
}

async function uploadSelectedFiles(itemId: number) {
  for (const [index, file] of imageFiles.value.entries()) {
    const shouldBePrimary = index === 0 && (props.item?.images.length ?? 0) === 0
    await inventory.uploadImage(itemId, file, shouldBePrimary)
  }
  for (const file of attachmentFiles.value) {
    await inventory.uploadAttachment(itemId, file)
  }
}

async function saveItem() {
  if (!validateAll()) return
  saving.value = true
  try {
    let detail: ItemDetail
    if (props.item) {
      detail = await inventory.updateItem(props.item.id, buildUpdatePayload())
      if (placementChanged()) {
        detail = await inventory.moveItem(props.item.id, {
          location_node_id: form.location_node_id,
          container_item_id: form.container_item_id,
          reason: '编辑物品资料'
        })
      }
    } else {
      detail = await inventory.createItem(buildCreatePayload())
    }

    await uploadSelectedFiles(detail.id)
    await inventory.openDetail(detail.id)
    const latestDetail = inventory.selectedItem ?? detail
    ElMessage.success(isEditing.value ? '已保存' : '已新增')
    emit('saved', latestDetail)
    emit('update:modelValue', false)
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    saving.value = false
  }
}

function goNext() {
  if (!validateStep(activeStep.value, false)) return
  activeStep.value = Math.min(activeStep.value + 1, steps.length - 1)
}

function goPrevious() {
  activeStep.value = Math.max(activeStep.value - 1, 0)
}

function closeDrawer() {
  emit('update:modelValue', false)
}
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    :title="drawerTitle"
    size="min(720px, 100%)"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="drawer-body">
      <el-steps :active="activeStep" finish-status="success" simple>
        <el-step v-for="step in steps" :key="step" :title="step" />
      </el-steps>

      <el-form :model="form" label-position="top" class="item-form">
        <section v-show="activeStep === 0" class="step-panel">
          <el-form-item label="分类" required>
            <el-select
              v-model="form.category_id"
              class="full-width"
              filterable
              placeholder="请选择分类"
            >
              <el-option
                v-for="category in categoryOptions"
                :key="category.value"
                :label="category.label"
                :value="category.value"
              />
            </el-select>
          </el-form-item>
        </section>

        <section v-show="activeStep === 1" class="step-panel">
          <el-form-item label="物品名称" required>
            <el-input v-model="form.name" maxlength="160" clearable />
          </el-form-item>

          <el-form-item label="说明">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="4"
              maxlength="1000"
              show-word-limit
            />
          </el-form-item>

          <div class="form-grid">
            <el-form-item label="状态" :required="!isEditing">
              <el-input v-if="isEditing" :model-value="item?.status_name ?? ''" disabled />
              <el-select
                v-else
                v-model="form.status_id"
                class="full-width"
                placeholder="请选择状态"
              >
                <el-option
                  v-for="status in activeStatuses"
                  :key="status.id"
                  :label="status.name"
                  :value="status.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="数量" :required="!isEditing">
              <el-input-number
                v-model="form.quantity"
                class="full-width"
                :disabled="isEditing"
                :min="0"
                :precision="2"
                controls-position="right"
              />
            </el-form-item>

            <el-form-item label="单位" required>
              <el-select
                v-model="form.unit"
                class="full-width"
                allow-create
                default-first-option
                filterable
              >
                <el-option
                  v-for="option in unitOptions"
                  :key="option.id"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="隐私">
              <el-select v-model="form.privacy_level" class="full-width">
                <el-option
                  v-for="option in privacyOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="归属人">
              <el-select v-model="form.owner_member_id" class="full-width" clearable filterable>
                <el-option
                  v-for="member in activeMembers"
                  :key="member.id"
                  :label="member.name"
                  :value="member.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="保管人">
              <el-select v-model="form.keeper_member_id" class="full-width" clearable filterable>
                <el-option
                  v-for="member in activeMembers"
                  :key="member.id"
                  :label="member.name"
                  :value="member.id"
                />
              </el-select>
            </el-form-item>
          </div>

          <el-form-item>
            <el-checkbox v-model="form.is_container">这个物品可作为容器</el-checkbox>
          </el-form-item>

          <el-form-item label="标签">
            <el-input
              v-model="form.tagsText"
              type="textarea"
              :rows="3"
              placeholder="多个标签用逗号或回车分隔"
            />
          </el-form-item>
        </section>

        <section v-show="activeStep === 2" class="step-panel">
          <el-alert
            v-if="isExitPlacementStatus"
            title="当前状态不需要设置位置或容器"
            type="info"
            :closable="false"
          />

          <template v-else>
            <el-radio-group v-model="placementType" class="placement-tabs">
              <el-radio-button label="location">放在位置</el-radio-button>
              <el-radio-button label="container">放入容器</el-radio-button>
            </el-radio-group>

            <el-form-item v-if="placementType === 'location'" label="位置" required>
              <el-select
                v-model="form.location_node_id"
                class="full-width"
                clearable
                filterable
                placeholder="请选择位置"
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
                v-model="form.container_item_id"
                class="full-width"
                clearable
                filterable
                placeholder="请选择容器"
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
        </section>

        <section v-show="activeStep === 3" class="step-panel">
          <CustomFieldInputs
            v-model="attributeValues"
            :definitions="selectedDefinitions"
          />
        </section>

        <section v-show="activeStep === 4" class="step-panel">
          <MediaUploader
            v-model:image-files="imageFiles"
            v-model:attachment-files="attachmentFiles"
            :images="item?.images ?? []"
            :attachments="item?.attachments ?? []"
          />
        </section>
      </el-form>
    </div>

    <template #footer>
      <div class="drawer-footer">
        <el-button :icon="Close" @click="closeDrawer">取消</el-button>
        <div class="footer-actions">
          <el-button :icon="ArrowLeft" :disabled="activeStep === 0" @click="goPrevious">
            上一步
          </el-button>
          <el-button
            v-if="activeStep < steps.length - 1"
            type="primary"
            :icon="ArrowRight"
            @click="goNext"
          >
            下一步
          </el-button>
          <el-button
            v-else
            type="primary"
            :icon="Check"
            :loading="saving"
            @click="saveItem"
          >
            保存
          </el-button>
        </div>
      </div>
    </template>
  </el-drawer>
</template>

<style scoped>
.drawer-body {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.item-form,
.step-panel {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.full-width {
  width: 100%;
}

.placement-tabs {
  margin-bottom: 4px;
}

.drawer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.footer-actions {
  display: flex;
  gap: 10px;
}

@media (max-width: 640px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .drawer-footer,
  .footer-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
