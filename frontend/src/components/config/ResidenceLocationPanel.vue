<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, type FormInstance } from 'element-plus'
import { CirclePlus, Edit, Plus } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../../api/client'
import type { LocationNode, Residence } from '../../api/configuration'
import { useConfigurationStore } from '../../stores/configuration'
import { dictionaryLabel, dictionaryOptions } from '../../utils/dictionaries'

interface LocationOption {
  id: number
  label: string
}

interface TreeNode {
  id: string
  label: string
  location?: LocationNode
  children?: TreeNode[]
}

const configuration = useConfigurationStore()
const { data } = storeToRefs(configuration)

const residenceFormRef = ref<FormInstance>()
const residenceEditFormRef = ref<FormInstance>()
const locationFormRef = ref<FormInstance>()
const locationEditFormRef = ref<FormInstance>()
const residenceEditOpen = ref(false)
const locationEditOpen = ref(false)
const editingResidence = ref<Residence | null>(null)
const editingLocation = ref<LocationNode | null>(null)
const residenceSaving = ref(false)
const locationSaving = ref(false)
const locationEditSaving = ref(false)

const residenceForm = reactive({
  name: '',
  description: '',
  address: ''
})

const residenceEditForm = reactive({
  name: '',
  description: '',
  address: '',
  sort_order: 0,
  is_active: true
})

const locationForm = reactive({
  residence_id: undefined as number | undefined,
  parent_id: null as number | null,
  name: '',
  node_type: ''
})

const locationEditForm = reactive({
  parent_id: null as number | null,
  name: '',
  node_type: '',
  icon: '',
  sort_order: 0,
  note: '',
  is_active: true
})

const residences = computed(() => data.value?.residences ?? [])
const locationTree = computed(() => data.value?.location_tree ?? [])
const locationNodeTypeOptions = computed(() =>
  dictionaryOptions(data.value, 'location_node_types')
)
const activeLocationNodeTypeValues = computed(() =>
  new Set(locationNodeTypeOptions.value.map((type) => type.value))
)

const locationNodeTypeEditOptions = computed(() => {
  const activeOptions = locationNodeTypeOptions.value.map(({ label, value }) => ({
    label,
    value,
    disabled: false
  }))
  const currentValue = locationEditForm.node_type
  if (!currentValue || activeLocationNodeTypeValues.value.has(currentValue)) return activeOptions

  return [
    ...activeOptions,
    {
      label: locationNodeTypeLabel(currentValue),
      value: currentValue,
      disabled: true
    }
  ]
})

const currentResidenceLocations = computed(() =>
  locationTree.value.filter((node) => node.residence_id === locationForm.residence_id)
)

const parentLocationOptions = computed<LocationOption[]>(() =>
  flattenLocationOptions(currentResidenceLocations.value)
)

const locationEditParentOptions = computed<LocationOption[]>(() => {
  if (!editingLocation.value) return []
  const residenceNodes = locationTree.value.filter(
    (node) => node.residence_id === editingLocation.value?.residence_id
  )
  return flattenLocationOptions(residenceNodes, collectLocationIds(editingLocation.value))
})

const groupedLocationTree = computed<TreeNode[]>(() =>
  residences.value.map((residence) => ({
    id: `residence-${residence.id}`,
    label: residence.name,
    children: toTreeNodes(locationTree.value.filter((node) => node.residence_id === residence.id))
  }))
)

watch(
  () => locationForm.residence_id,
  () => {
    locationForm.parent_id = null
  }
)

watch(
  locationNodeTypeOptions,
  (options) => {
    if (!activeLocationNodeTypeValues.value.has(locationForm.node_type)) {
      locationForm.node_type = options[0]?.value ?? ''
    }
  },
  { immediate: true }
)

function locationNodeTypeLabel(value: string) {
  return dictionaryLabel(data.value, 'location_node_types', value)
}

function toTreeNodes(nodes: LocationNode[]): TreeNode[] {
  return nodes.map((node) => ({
    id: `location-${node.id}`,
    label: `${node.name} · ${locationNodeTypeLabel(node.node_type)}`,
    location: node,
    children: toTreeNodes(node.children ?? [])
  }))
}

function collectLocationIds(node: LocationNode): Set<number> {
  const ids = new Set<number>([node.id])
  for (const child of node.children ?? []) {
    for (const childId of collectLocationIds(child)) {
      ids.add(childId)
    }
  }
  return ids
}

function flattenLocationOptions(nodes: LocationNode[], excludedIds = new Set<number>(), depth = 0): LocationOption[] {
  return nodes.flatMap((node) => {
    if (excludedIds.has(node.id)) return []
    return [
      { id: node.id, label: `${'  '.repeat(depth)}${node.name}` },
      ...flattenLocationOptions(node.children ?? [], excludedIds, depth + 1)
    ]
  })
}

async function validateForm(form?: FormInstance) {
  if (!form) return false
  return form.validate().then(() => true).catch(() => false)
}

function trimResidenceForm() {
  residenceForm.name = residenceForm.name.trim()
  residenceForm.description = residenceForm.description.trim()
  residenceForm.address = residenceForm.address.trim()
}

function trimResidenceEditForm() {
  residenceEditForm.name = residenceEditForm.name.trim()
  residenceEditForm.description = residenceEditForm.description.trim()
  residenceEditForm.address = residenceEditForm.address.trim()
}

function trimLocationForm() {
  locationForm.name = locationForm.name.trim()
}

function trimLocationEditForm() {
  locationEditForm.name = locationEditForm.name.trim()
  locationEditForm.icon = locationEditForm.icon.trim()
  locationEditForm.note = locationEditForm.note.trim()
}

async function saveResidence() {
  trimResidenceForm()
  const valid = await validateForm(residenceFormRef.value)
  if (!valid) return

  residenceSaving.value = true
  try {
    await configuration.createResidence({
      name: residenceForm.name.trim(),
      description: residenceForm.description.trim(),
      address: residenceForm.address.trim()
    })
    Object.assign(residenceForm, { name: '', description: '', address: '' })
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    residenceSaving.value = false
  }
}

function openResidenceEdit(residence: Residence) {
  editingResidence.value = residence
  Object.assign(residenceEditForm, {
    name: residence.name,
    description: residence.description,
    address: residence.address,
    sort_order: residence.sort_order,
    is_active: residence.is_active
  })
  residenceEditOpen.value = true
}

function clearResidenceEdit() {
  editingResidence.value = null
  Object.assign(residenceEditForm, {
    name: '',
    description: '',
    address: '',
    sort_order: 0,
    is_active: true
  })
}

async function updateResidence() {
  trimResidenceEditForm()
  const valid = await validateForm(residenceEditFormRef.value)
  if (!valid || !editingResidence.value) return

  residenceSaving.value = true
  try {
    await configuration.updateResidence(editingResidence.value.id, {
      name: residenceEditForm.name.trim(),
      description: residenceEditForm.description.trim(),
      address: residenceEditForm.address.trim(),
      sort_order: Number(residenceEditForm.sort_order) || 0,
      is_active: residenceEditForm.is_active
    })
    residenceEditOpen.value = false
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    residenceSaving.value = false
  }
}

function openLocationEdit(location: LocationNode) {
  editingLocation.value = location
  Object.assign(locationEditForm, {
    parent_id: location.parent_id,
    name: location.name,
    node_type: location.node_type,
    icon: location.icon,
    sort_order: location.sort_order,
    note: location.note,
    is_active: location.is_active
  })
  locationEditOpen.value = true
}

function clearLocationEdit() {
  editingLocation.value = null
  Object.assign(locationEditForm, {
    parent_id: null,
    name: '',
    node_type: '',
    icon: '',
    sort_order: 0,
    note: '',
    is_active: true
  })
}

async function updateLocationNode() {
  trimLocationEditForm()
  const valid = await validateForm(locationEditFormRef.value)
  if (!valid || !editingLocation.value) return

  locationEditSaving.value = true
  try {
    await configuration.updateLocationNode(editingLocation.value.id, {
      parent_id: locationEditForm.parent_id,
      name: locationEditForm.name.trim(),
      node_type: locationEditForm.node_type,
      icon: locationEditForm.icon.trim(),
      sort_order: Number(locationEditForm.sort_order) || 0,
      note: locationEditForm.note.trim(),
      is_active: locationEditForm.is_active
    })
    locationEditOpen.value = false
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    locationEditSaving.value = false
  }
}

async function saveLocation() {
  trimLocationForm()
  const valid = await validateForm(locationFormRef.value)
  if (!valid) return
  if (!locationForm.residence_id) return
  if (!locationForm.node_type) {
    ElMessage.error('请选择类型')
    return
  }

  locationSaving.value = true
  try {
    await configuration.createLocationNode({
      residence_id: locationForm.residence_id,
      parent_id: locationForm.parent_id,
      name: locationForm.name.trim(),
      node_type: locationForm.node_type
    })
    Object.assign(locationForm, {
      parent_id: null,
      name: '',
      node_type: locationNodeTypeOptions.value[0]?.value ?? ''
    })
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    locationSaving.value = false
  }
}
</script>

<template>
  <div class="panel-grid two-columns">
    <section class="tool-section">
      <h2>住宅</h2>
      <el-form
        ref="residenceFormRef"
        :model="residenceForm"
        label-position="top"
        class="compact-form"
      >
        <el-form-item label="住宅名称" prop="name" :rules="[{ required: true, message: '请输入住宅名称' }]">
          <el-input v-model="residenceForm.name" maxlength="40" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="residenceForm.description" maxlength="120" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="residenceForm.address" maxlength="160" />
        </el-form-item>
        <el-button type="primary" :icon="Plus" :loading="residenceSaving" @click="saveResidence">
          保存住宅
        </el-button>
      </el-form>

      <el-table :data="residences" size="small" class="data-table">
        <el-table-column prop="name" label="名称" min-width="120" />
        <el-table-column prop="address" label="地址" min-width="180" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
        <el-table-column prop="is_active" label="状态" width="92">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="92" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" :icon="Edit" @click="openResidenceEdit(row)">
              编辑
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="tool-section">
      <h2>位置</h2>
      <el-form
        ref="locationFormRef"
        :model="locationForm"
        label-position="top"
        class="compact-form"
      >
        <div class="form-row">
          <el-form-item label="住宅" prop="residence_id" :rules="[{ required: true, message: '请选择住宅' }]">
            <el-select v-model="locationForm.residence_id" class="full-width">
              <el-option
                v-for="residence in residences"
                :key="residence.id"
                :label="residence.name"
                :value="residence.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="上级位置">
            <el-select
              v-model="locationForm.parent_id"
              class="full-width"
              clearable
              :disabled="!locationForm.residence_id"
            >
              <el-option
                v-for="location in parentLocationOptions"
                :key="location.id"
                :label="location.label"
                :value="location.id"
              />
            </el-select>
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="位置名称" prop="name" :rules="[{ required: true, message: '请输入位置名称' }]">
            <el-input v-model="locationForm.name" maxlength="40" />
          </el-form-item>
          <el-form-item label="类型" prop="node_type" :rules="[{ required: true, message: '请选择类型' }]">
            <el-select v-model="locationForm.node_type" class="full-width">
              <el-option
                v-for="type in locationNodeTypeOptions"
                :key="type.value"
                :label="type.label"
                :value="type.value"
              />
            </el-select>
          </el-form-item>
        </div>
        <el-button type="primary" :icon="CirclePlus" :loading="locationSaving" @click="saveLocation">
          保存位置
        </el-button>
      </el-form>

      <div class="tree-wrap">
        <el-tree
          :data="groupedLocationTree"
          node-key="id"
          default-expand-all
          empty-text="暂无位置"
        >
          <template #default="{ data: nodeData }">
            <div class="tree-node-row">
              <span>{{ nodeData.label }}</span>
              <el-tag v-if="nodeData.location" size="small" :type="nodeData.location.is_active ? 'success' : 'info'">
                {{ nodeData.location.is_active ? '启用' : '停用' }}
              </el-tag>
              <el-button
                v-if="nodeData.location"
                text
                type="primary"
                :icon="Edit"
                @click.stop="openLocationEdit(nodeData.location)"
              >
                编辑
              </el-button>
            </div>
          </template>
        </el-tree>
      </div>
    </section>
  </div>

  <el-dialog
    v-model="residenceEditOpen"
    title="编辑住宅"
    width="520px"
    destroy-on-close
    @closed="clearResidenceEdit"
  >
    <el-form
      ref="residenceEditFormRef"
      :model="residenceEditForm"
      label-position="top"
      class="compact-form"
    >
      <el-form-item label="住宅名称" prop="name" :rules="[{ required: true, message: '请输入住宅名称' }]">
        <el-input v-model="residenceEditForm.name" maxlength="40" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="residenceEditForm.description" maxlength="120" />
      </el-form-item>
      <el-form-item label="地址">
        <el-input v-model="residenceEditForm.address" maxlength="160" />
      </el-form-item>
      <div class="form-row">
        <el-form-item label="排序">
          <el-input-number
            v-model="residenceEditForm.sort_order"
            :min="0"
            :step="1"
            controls-position="right"
            class="full-width"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch
            v-model="residenceEditForm.is_active"
            active-text="启用"
            inactive-text="停用"
          />
        </el-form-item>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="residenceEditOpen = false">取消</el-button>
      <el-button type="primary" :loading="residenceSaving" @click="updateResidence">
        保存
      </el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="locationEditOpen"
    title="编辑位置"
    width="520px"
    destroy-on-close
    @closed="clearLocationEdit"
  >
    <el-form
      ref="locationEditFormRef"
      :model="locationEditForm"
      label-position="top"
      class="compact-form"
    >
      <el-form-item label="上级位置">
        <el-select v-model="locationEditForm.parent_id" class="full-width" clearable>
          <el-option
            v-for="location in locationEditParentOptions"
            :key="location.id"
            :label="location.label"
            :value="location.id"
          />
        </el-select>
      </el-form-item>
      <div class="form-row">
        <el-form-item label="位置名称" prop="name" :rules="[{ required: true, message: '请输入位置名称' }]">
          <el-input v-model="locationEditForm.name" maxlength="40" />
        </el-form-item>
        <el-form-item label="类型" prop="node_type" :rules="[{ required: true, message: '请选择类型' }]">
          <el-select v-model="locationEditForm.node_type" class="full-width">
            <el-option
              v-for="type in locationNodeTypeEditOptions"
              :key="type.value"
              :label="type.label"
              :value="type.value"
              :disabled="type.disabled"
            />
          </el-select>
        </el-form-item>
      </div>
      <div class="form-row">
        <el-form-item label="图标">
          <el-input v-model="locationEditForm.icon" maxlength="40" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number
            v-model="locationEditForm.sort_order"
            :min="0"
            :step="1"
            controls-position="right"
            class="full-width"
          />
        </el-form-item>
      </div>
      <el-form-item label="备注">
        <el-input v-model="locationEditForm.note" type="textarea" :rows="3" maxlength="200" />
      </el-form-item>
      <el-form-item label="状态">
        <el-switch
          v-model="locationEditForm.is_active"
          active-text="启用"
          inactive-text="停用"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="locationEditOpen = false">取消</el-button>
      <el-button type="primary" :loading="locationEditSaving" @click="updateLocationNode">
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.panel-grid {
  display: grid;
  gap: 18px;
}

.two-columns {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}

.tool-section {
  min-width: 0;
  padding: 18px;
  background: #fff;
  border: 1px solid #eadfce;
  border-radius: 8px;
}

.tool-section h2 {
  margin: 0 0 14px;
  color: #26342e;
  font-size: 16px;
}

.compact-form {
  margin-bottom: 16px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.full-width {
  width: 100%;
}

.data-table,
.tree-wrap {
  margin-top: 14px;
}

.tree-node-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.tree-wrap {
  min-height: 180px;
  padding: 10px;
  border: 1px solid #edf0eb;
  border-radius: 6px;
}

@media (max-width: 960px) {
  .two-columns,
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
