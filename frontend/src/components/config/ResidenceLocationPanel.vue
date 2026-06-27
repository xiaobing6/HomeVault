<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, type FormInstance } from 'element-plus'
import { CirclePlus, Edit, Plus } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../../api/client'
import type { LocationNode, Residence } from '../../api/configuration'
import { useConfigurationStore } from '../../stores/configuration'

interface LocationOption {
  id: number
  label: string
}

interface TreeNode {
  id: string
  label: string
  children?: TreeNode[]
}

const configuration = useConfigurationStore()
const { data } = storeToRefs(configuration)

const residenceFormRef = ref<FormInstance>()
const residenceEditFormRef = ref<FormInstance>()
const locationFormRef = ref<FormInstance>()
const residenceEditOpen = ref(false)
const editingResidence = ref<Residence | null>(null)
const residenceSaving = ref(false)
const locationSaving = ref(false)

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
  node_type: 'room'
})

const locationTypes = [
  { label: '房间', value: 'room' },
  { label: '区域', value: 'area' },
  { label: '柜体', value: 'cabinet' },
  { label: '层架', value: 'shelf' },
  { label: '箱盒', value: 'box' },
  { label: '其他', value: 'other' }
]

const residences = computed(() => data.value?.residences ?? [])
const locationTree = computed(() => data.value?.location_tree ?? [])

const currentResidenceLocations = computed(() =>
  locationTree.value.filter((node) => node.residence_id === locationForm.residence_id)
)

const parentLocationOptions = computed<LocationOption[]>(() => {
  const flatten = (nodes: LocationNode[], depth = 0): LocationOption[] =>
    nodes.flatMap((node) => [
      { id: node.id, label: `${'　'.repeat(depth)}${node.name}` },
      ...flatten(node.children ?? [], depth + 1)
    ])

  return flatten(currentResidenceLocations.value)
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

function toTreeNodes(nodes: LocationNode[]): TreeNode[] {
  return nodes.map((node) => ({
    id: `location-${node.id}`,
    label: `${node.name} · ${node.node_type}`,
    children: toTreeNodes(node.children ?? [])
  }))
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

async function saveLocation() {
  trimLocationForm()
  const valid = await validateForm(locationFormRef.value)
  if (!valid) return
  if (!locationForm.residence_id) return

  locationSaving.value = true
  try {
    await configuration.createLocationNode({
      residence_id: locationForm.residence_id,
      parent_id: locationForm.parent_id,
      name: locationForm.name.trim(),
      node_type: locationForm.node_type
    })
    Object.assign(locationForm, { parent_id: null, name: '', node_type: 'room' })
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
                v-for="type in locationTypes"
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
        />
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
