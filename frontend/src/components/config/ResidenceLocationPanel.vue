<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, type FormInstance, type UploadUserFile } from 'element-plus'
import { ArrowLeft, Calendar, Edit, House, Location, Memo, Picture, Plus, PriceTag, User } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../../api/client'
import type { LocationNode, Residence } from '../../api/configuration'
import { useConfigurationStore } from '../../stores/configuration'
import { dictionaryLabel, dictionaryOptions } from '../../utils/dictionaries'
import ProtectedImage from '../items/ProtectedImage.vue'

interface LocationOption {
  id: number
  label: string
}

interface LocationCard {
  node: LocationNode
  residence?: Residence
  parentName: string
  path: string
  depth: number
}

const configuration = useConfigurationStore()
const { data } = storeToRefs(configuration)

const activeResourceTab = ref('residences')
const residenceCreateOpen = ref(false)
const residenceEditOpen = ref(false)
const locationCreateOpen = ref(false)
const locationEditOpen = ref(false)
const selectedResidence = ref<Residence | null>(null)
const selectedLocation = ref<LocationNode | null>(null)
const editingResidence = ref<Residence | null>(null)
const editingLocation = ref<LocationNode | null>(null)
const residenceSaving = ref(false)
const locationSaving = ref(false)
const locationEditSaving = ref(false)
const residenceImageFiles = ref<UploadUserFile[]>([])
const residenceEditImageFiles = ref<UploadUserFile[]>([])
const locationResidenceFilter = ref<number | '' | null | undefined>('')
const locationTypeFilter = ref<string | null | undefined>('')

const residenceFormRef = ref<FormInstance>()
const residenceEditFormRef = ref<FormInstance>()
const locationFormRef = ref<FormInstance>()
const locationEditFormRef = ref<FormInstance>()

const residenceForm = reactive({
  name: '',
  description: '',
  address: ''
})

const residenceEditForm = reactive({
  name: '',
  description: '',
  address: '',
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
const locationNodeTypeOptions = computed(() => dictionaryOptions(data.value, 'location_node_types'))
const activeLocationNodeTypeValues = computed(() => new Set(locationNodeTypeOptions.value.map((type) => type.value)))

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

const parentLocationOptions = computed<LocationOption[]>(() => flattenLocationOptions(currentResidenceLocations.value))

const locationEditParentOptions = computed<LocationOption[]>(() => {
  if (!editingLocation.value) return []
  const residenceNodes = locationTree.value.filter((node) => node.residence_id === editingLocation.value?.residence_id)
  return flattenLocationOptions(residenceNodes, collectLocationIds(editingLocation.value))
})

const selectedResidenceDetail = computed(() => {
  if (!selectedResidence.value) return null
  return residences.value.find((residence) => residence.id === selectedResidence.value?.id) ?? selectedResidence.value
})

const selectedLocationDetail = computed(() => {
  if (!selectedLocation.value) return null
  return findLocationById(locationTree.value, selectedLocation.value.id) ?? selectedLocation.value
})

const selectedLocationResidence = computed(() => {
  if (!selectedLocationDetail.value) return null
  return residences.value.find((residence) => residence.id === selectedLocationDetail.value?.residence_id) ?? null
})

const isShowingDetail = computed(() => Boolean(selectedResidenceDetail.value || selectedLocationDetail.value))

const allLocationCards = computed<LocationCard[]>(() =>
  residences.value.flatMap((residence) =>
    toLocationCards(
      locationTree.value.filter((node) => node.residence_id === residence.id),
      residence
    )
  )
)

const filteredLocationCards = computed(() =>
  allLocationCards.value.filter((card) => {
    const selectedResidenceId = locationResidenceFilter.value
    const selectedLocationType = locationTypeFilter.value
    const matchesResidence = !hasResidenceFilter(selectedResidenceId) || card.node.residence_id === selectedResidenceId
    const matchesType = !hasLocationTypeFilter(selectedLocationType) || card.node.node_type === selectedLocationType
    return matchesResidence && matchesType
  })
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

function statusType(isActive: boolean) {
  return isActive ? 'success' : 'info'
}

function statusText(isActive: boolean) {
  return isActive ? '启用' : '停用'
}

function formatDateTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '未记录'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

function formatPerson(name?: string | null) {
  return name || '系统'
}

function hasResidenceFilter(value: number | '' | null | undefined): value is number {
  return typeof value === 'number'
}

function hasLocationTypeFilter(value: string | null | undefined) {
  return typeof value === 'string' && value.length > 0
}

function toLocationCards(nodes: LocationNode[], residence: Residence, parentName = '', depth = 0): LocationCard[] {
  return nodes.flatMap((node) => {
    const path = parentName ? `${parentName} / ${node.name}` : node.name
    return [
      { node, residence, parentName, path, depth },
      ...toLocationCards(node.children ?? [], residence, path, depth + 1)
    ]
  })
}

function findLocationById(nodes: LocationNode[], locationId: number): LocationNode | null {
  for (const node of nodes) {
    if (node.id === locationId) return node
    const child = findLocationById(node.children ?? [], locationId)
    if (child) return child
  }
  return null
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

function resetResidenceForm() {
  Object.assign(residenceForm, { name: '', description: '', address: '' })
  residenceImageFiles.value = []
}

function resetLocationForm() {
  Object.assign(locationForm, {
    residence_id: locationResidenceFilter.value || residences.value[0]?.id,
    parent_id: null,
    name: '',
    node_type: locationNodeTypeOptions.value[0]?.value ?? ''
  })
}

function handleResourceTabChange() {
  selectedResidence.value = null
  selectedLocation.value = null
}

function openResidenceCreate() {
  resetResidenceForm()
  residenceCreateOpen.value = true
}

function openLocationCreate() {
  resetLocationForm()
  locationCreateOpen.value = true
}

function selectResidence(residence: Residence) {
  selectedResidence.value = residence
}

function selectLocation(location: LocationNode) {
  selectedLocation.value = location
}

function backToList() {
  selectedResidence.value = null
  selectedLocation.value = null
}

async function saveResidence() {
  trimResidenceForm()
  const valid = await validateForm(residenceFormRef.value)
  if (!valid) return

  residenceSaving.value = true
  try {
    const residence = await configuration.createResidence({
      name: residenceForm.name.trim(),
      description: residenceForm.description.trim(),
      address: residenceForm.address.trim()
    })
    const imageFile = residenceImageFiles.value[0]?.raw
    if (imageFile) {
      await configuration.uploadResidenceImage(residence.id, imageFile)
    }
    resetResidenceForm()
    residenceCreateOpen.value = false
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
    is_active: residence.is_active
  })
  residenceEditImageFiles.value = []
  residenceEditOpen.value = true
}

function clearResidenceEdit() {
  editingResidence.value = null
  Object.assign(residenceEditForm, {
    name: '',
    description: '',
    address: '',
    is_active: true
  })
  residenceEditImageFiles.value = []
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
      is_active: residenceEditForm.is_active
    })
    const imageFile = residenceEditImageFiles.value[0]?.raw
    if (imageFile) {
      await configuration.uploadResidenceImage(editingResidence.value.id, imageFile)
    }
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
    resetLocationForm()
    locationCreateOpen.value = false
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    locationSaving.value = false
  }
}
</script>

<template>
  <section class="residence-location-panel" :class="{ 'is-detail': isShowingDetail }">
    <div v-if="isShowingDetail" class="resource-detail-shell">
      <div v-if="selectedResidenceDetail" class="resource-detail">
        <div class="detail-breadcrumb">
          <span>住宅与位置</span>
          <span>/</span>
          <span>住宅</span>
          <span>/</span>
          <strong>{{ selectedResidenceDetail.name }}</strong>
        </div>

        <el-button class="back-button" :icon="ArrowLeft" @click="backToList">返回</el-button>

        <div class="detail-cover residence-cover">
          <ProtectedImage
            v-if="selectedResidenceDetail.image_url"
            :src="selectedResidenceDetail.image_url"
            :alt="selectedResidenceDetail.name"
          >
            <el-icon class="cover-placeholder"><Picture /></el-icon>
          </ProtectedImage>
          <el-icon v-else class="cover-placeholder"><House /></el-icon>
          <el-button class="detail-edit" :icon="Edit" round @click="openResidenceEdit(selectedResidenceDetail)">
            编辑
          </el-button>
        </div>

        <article class="detail-card">
          <div class="detail-title-row">
            <h2>{{ selectedResidenceDetail.name }}</h2>
            <el-tag size="small" :type="statusType(selectedResidenceDetail.is_active)">
              {{ statusText(selectedResidenceDetail.is_active) }}
            </el-tag>
          </div>

          <div class="detail-list">
            <div class="detail-line">
              <el-icon><Location /></el-icon>
              <div>
                <span>地址</span>
                <p>{{ selectedResidenceDetail.address || '未填写' }}</p>
              </div>
            </div>
            <div class="detail-line">
              <el-icon><Memo /></el-icon>
              <div>
                <span>描述</span>
                <p>{{ selectedResidenceDetail.description || '未填写' }}</p>
              </div>
            </div>
            <div class="detail-line">
              <el-icon><Calendar /></el-icon>
              <div>
                <span>新建时间</span>
                <p>{{ formatDateTime(selectedResidenceDetail.created_at) }}</p>
              </div>
            </div>
            <div class="detail-line">
              <el-icon><User /></el-icon>
              <div>
                <span>新建人</span>
                <p>{{ formatPerson(selectedResidenceDetail.created_by_name) }}</p>
              </div>
            </div>
            <div class="detail-line">
              <el-icon><Calendar /></el-icon>
              <div>
                <span>更新时间</span>
                <p>{{ formatDateTime(selectedResidenceDetail.updated_at) }}</p>
              </div>
            </div>
            <div class="detail-line">
              <el-icon><User /></el-icon>
              <div>
                <span>更新人</span>
                <p>{{ formatPerson(selectedResidenceDetail.updated_by_name) }}</p>
              </div>
            </div>
          </div>
        </article>
      </div>

      <div v-else-if="selectedLocationDetail" class="resource-detail">
        <div class="detail-breadcrumb">
          <span>住宅与位置</span>
          <span>/</span>
          <span>位置</span>
          <span>/</span>
          <strong>{{ selectedLocationDetail.name }}</strong>
        </div>

        <el-button class="back-button" :icon="ArrowLeft" @click="backToList">返回</el-button>

        <div class="detail-cover location-cover">
          <el-icon class="cover-placeholder"><Location /></el-icon>
          <el-button class="detail-edit" :icon="Edit" round @click="openLocationEdit(selectedLocationDetail)">
            编辑
          </el-button>
        </div>

        <article class="detail-card">
          <div class="detail-title-row">
            <h2>{{ selectedLocationDetail.name }}</h2>
            <el-tag size="small" :type="statusType(selectedLocationDetail.is_active)">
              {{ statusText(selectedLocationDetail.is_active) }}
            </el-tag>
          </div>

          <div class="detail-list">
            <div class="detail-line">
              <el-icon><House /></el-icon>
              <div>
                <span>住宅</span>
                <p>{{ selectedLocationResidence?.name || '未关联住宅' }}</p>
              </div>
            </div>
            <div class="detail-line">
              <el-icon><PriceTag /></el-icon>
              <div>
                <span>类型</span>
                <p>{{ locationNodeTypeLabel(selectedLocationDetail.node_type) }}</p>
              </div>
            </div>
            <div class="detail-line">
              <el-icon><Memo /></el-icon>
              <div>
                <span>备注</span>
                <p>{{ selectedLocationDetail.note || '未填写' }}</p>
              </div>
            </div>
          </div>
        </article>
      </div>
    </div>

    <div v-else class="resource-list-shell">
      <div class="section-heading">
        <h1>住宅与位置</h1>
      </div>

      <div class="resource-tabs-shell">
        <div class="resource-tab-actions">
          <el-button
            v-if="activeResourceTab === 'residences'"
            type="primary"
            :icon="Plus"
            round
            @click="openResidenceCreate"
          >
            新建住宅
          </el-button>
          <template v-else>
            <el-select
              v-model="locationResidenceFilter"
              placeholder="全部住宅"
              clearable
              class="toolbar-select"
            >
              <el-option
                v-for="residence in residences"
                :key="residence.id"
                :label="residence.name"
                :value="residence.id"
              />
            </el-select>
            <el-select v-model="locationTypeFilter" placeholder="位置类型" clearable class="toolbar-select">
              <el-option
                v-for="type in locationNodeTypeOptions"
                :key="type.value"
                :label="type.label"
                :value="type.value"
              />
            </el-select>
            <el-button type="primary" :icon="Plus" round @click="openLocationCreate">
              新建位置
            </el-button>
          </template>
        </div>

        <el-tabs v-model="activeResourceTab" class="resource-tabs" @tab-change="handleResourceTabChange">
          <el-tab-pane label="住宅" name="residences">
            <div class="resource-list">
              <div v-if="residences.length" class="residence-card-grid">
                <button
                  v-for="residence in residences"
                  :key="residence.id"
                  type="button"
                  class="resource-card residence-card"
                  @click="selectResidence(residence)"
                >
                  <div class="card-cover residence-cover">
                    <ProtectedImage v-if="residence.image_url" :src="residence.image_url" :alt="residence.name">
                      <el-icon class="cover-placeholder"><Picture /></el-icon>
                    </ProtectedImage>
                    <el-icon v-else class="cover-placeholder"><House /></el-icon>
                  </div>
                  <div class="card-body">
                    <div class="card-title-row">
                      <h3>{{ residence.name }}</h3>
                    </div>
                    <p>{{ residence.address || '未填写地址' }}</p>
                    <span>{{ residence.description || '未填写描述' }}</span>
                    <small>更新于 {{ formatDateTime(residence.updated_at) }}</small>
                    <div class="card-status-line">
                      <span class="status-dot" :class="{ inactive: !residence.is_active }" />
                      {{ statusText(residence.is_active) }}
                    </div>
                  </div>
                </button>
              </div>
              <el-empty v-else description="暂无住宅" />
            </div>
          </el-tab-pane>

          <el-tab-pane label="位置" name="locations">
            <div class="resource-list">
              <div v-if="filteredLocationCards.length" class="location-card-grid">
                <button
                  v-for="card in filteredLocationCards"
                  :key="card.node.id"
                  type="button"
                  class="resource-card location-card"
                  @click="selectLocation(card.node)"
                >
                  <div class="card-cover location-cover">
                    <el-icon class="cover-placeholder"><Location /></el-icon>
                  </div>
                  <div class="card-body">
                    <div class="card-title-row">
                      <h3>{{ card.node.name }}</h3>
                    </div>
                    <p>{{ card.residence?.name || '未关联住宅' }}</p>
                    <span>{{ locationNodeTypeLabel(card.node.node_type) }}</span>
                    <small v-if="card.parentName">{{ card.parentName }}</small>
                    <div class="card-status-line">
                      <span class="status-dot" :class="{ inactive: !card.node.is_active }" />
                      {{ statusText(card.node.is_active) }}
                    </div>
                  </div>
                </button>
              </div>
              <el-empty v-else description="暂无位置" />
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </section>

  <el-dialog
    v-model="residenceCreateOpen"
    title="新建住宅"
    width="560px"
    class="resource-dialog"
    destroy-on-close
    @closed="resetResidenceForm"
  >
    <el-form ref="residenceFormRef" :model="residenceForm" label-position="top" class="compact-form">
      <el-form-item label="住宅名称" prop="name" :rules="[{ required: true, message: '请输入住宅名称' }]">
        <el-input v-model="residenceForm.name" maxlength="40" placeholder="例如：主宅、老家、仓库" />
      </el-form-item>
      <el-form-item label="地址">
        <el-input v-model="residenceForm.address" maxlength="160" placeholder="填写门牌、楼栋或区域" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input
          v-model="residenceForm.description"
          type="textarea"
          :rows="3"
          maxlength="120"
          placeholder="记录用途、楼层或居住说明"
        />
      </el-form-item>
      <el-form-item label="图片">
        <el-upload
          v-model:file-list="residenceImageFiles"
          accept="image/*"
          :auto-upload="false"
          :limit="1"
          list-type="picture-card"
        >
          <el-icon><Plus /></el-icon>
        </el-upload>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="residenceCreateOpen = false">取消</el-button>
      <el-button type="primary" :loading="residenceSaving" @click="saveResidence">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="residenceEditOpen"
    title="编辑住宅"
    width="560px"
    class="resource-dialog"
    destroy-on-close
    @closed="clearResidenceEdit"
  >
    <el-form ref="residenceEditFormRef" :model="residenceEditForm" label-position="top" class="compact-form">
      <el-form-item label="住宅名称" prop="name" :rules="[{ required: true, message: '请输入住宅名称' }]">
        <el-input v-model="residenceEditForm.name" maxlength="40" />
      </el-form-item>
      <el-form-item label="地址">
        <el-input v-model="residenceEditForm.address" maxlength="160" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="residenceEditForm.description" type="textarea" :rows="3" maxlength="120" />
      </el-form-item>
      <div class="form-row">
        <el-form-item label="图片">
          <el-upload
            v-model:file-list="residenceEditImageFiles"
            accept="image/*"
            :auto-upload="false"
            :limit="1"
            list-type="picture-card"
          >
            <el-icon><Plus /></el-icon>
          </el-upload>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="residenceEditForm.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="residenceEditOpen = false">取消</el-button>
      <el-button type="primary" :loading="residenceSaving" @click="updateResidence">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="locationCreateOpen"
    title="新建位置"
    width="560px"
    class="resource-dialog"
    destroy-on-close
    @closed="resetLocationForm"
  >
    <el-form ref="locationFormRef" :model="locationForm" label-position="top" class="compact-form">
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
          <el-select v-model="locationForm.parent_id" class="full-width" clearable :disabled="!locationForm.residence_id">
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
    </el-form>
    <template #footer>
      <el-button @click="locationCreateOpen = false">取消</el-button>
      <el-button type="primary" :loading="locationSaving" @click="saveLocation">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="locationEditOpen"
    title="编辑位置"
    width="560px"
    class="resource-dialog"
    destroy-on-close
    @closed="clearLocationEdit"
  >
    <el-form ref="locationEditFormRef" :model="locationEditForm" label-position="top" class="compact-form">
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
        <el-switch v-model="locationEditForm.is_active" active-text="启用" inactive-text="停用" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="locationEditOpen = false">取消</el-button>
      <el-button type="primary" :loading="locationEditSaving" @click="updateLocationNode">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.residence-location-panel {
  min-width: 0;
  width: 100%;
}

.resource-list-shell {
  min-width: 0;
  width: 100%;
}

.resource-detail-shell {
  width: 100%;
  max-width: 1040px;
  margin: 0 auto;
  padding-inline: clamp(24px, 4vw, 48px);
}

.section-heading {
  margin-bottom: 16px;
}

.section-heading h1 {
  margin: 0;
  color: #1f2c27;
  font-size: 20px;
  font-weight: 800;
}

.resource-tabs-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  min-width: 0;
}

.resource-tab-actions {
  grid-column: 2;
  grid-row: 1;
  justify-self: end;
  z-index: 2;
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: -6px;
  margin-left: 16px;
}

.resource-tabs {
  grid-column: 1 / -1;
  grid-row: 1;
  min-width: 0;
}

.resource-tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
}

.resource-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background-color: #dfe5ee;
}

.resource-tabs :deep(.el-tabs__content) {
  overflow: visible;
}

.resource-list,
.resource-detail {
  display: grid;
  gap: 18px;
}

.toolbar-select {
  width: 132px;
}

.residence-card-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.location-card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.resource-card {
  display: block;
  width: 100%;
  min-width: 0;
  appearance: none;
  padding: 0;
  overflow: hidden;
  font: inherit;
  color: inherit;
  text-align: left;
  background: #fff;
  border: 1px solid #e4e8ee;
  border-radius: 8px;
  box-shadow: 0 10px 24px rgba(37, 52, 45, 0.06);
  cursor: pointer;
  transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
}

.resource-card:hover {
  border-color: #9cc4e7;
  box-shadow: 0 14px 30px rgba(37, 52, 45, 0.1);
  transform: translateY(-2px);
}

.card-cover,
.detail-cover {
  position: relative;
  display: grid;
  place-items: center;
  overflow: hidden;
}

.card-cover {
  aspect-ratio: 16 / 9;
  min-height: 220px;
}

.residence-cover {
  background: linear-gradient(135deg, #d8e6ef, #efe0c5);
}

.location-cover {
  background: linear-gradient(135deg, #dce7dd, #cbdbee);
}

.cover-placeholder {
  color: rgba(31, 44, 39, 0.42);
  font-size: 42px;
}

.card-body {
  display: grid;
  gap: 8px;
  padding: 14px 16px 16px;
}

.card-title-row,
.detail-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-width: 0;
}

.card-title-row h3,
.detail-title-row h2 {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  color: #1f2c27;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-title-row h3 {
  font-size: 16px;
  font-weight: 800;
}

.detail-title-row h2 {
  font-size: 24px;
}

.card-body p,
.card-body span,
.card-body small {
  margin: 0;
  overflow: hidden;
  color: #6d7670;
  font-size: 13px;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-status-line {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  color: #4f6258;
  font-size: 12px;
}

.status-dot {
  width: 6px;
  height: 6px;
  background: #2fc56c;
  border-radius: 50%;
}

.status-dot.inactive {
  background: #a0a8a3;
}

.detail-breadcrumb {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  color: #8a938e;
  font-size: 13px;
}

.detail-breadcrumb strong {
  color: #2172c4;
}

.back-button {
  width: fit-content;
}

.detail-cover {
  min-height: 300px;
  border-radius: 8px;
}

.detail-edit {
  position: absolute;
  top: 16px;
  right: 16px;
  color: #25342d;
  background: rgba(255, 255, 255, 0.9);
  border: none;
}

.detail-card {
  display: grid;
  gap: 18px;
  padding: 24px;
  background: #fff;
  border: 1px solid #e4e8ee;
  border-radius: 8px;
}

.detail-list {
  display: grid;
}

.detail-line {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 10px;
  padding: 14px 0;
  border-top: 1px solid #eef1f4;
}

.detail-line:first-child {
  border-top: none;
}

.detail-line .el-icon {
  margin-top: 2px;
  color: #8a938e;
}

.detail-line span {
  display: block;
  margin-bottom: 6px;
  color: #8a938e;
  font-size: 12px;
}

.detail-line p {
  margin: 0;
  color: #1f2c27;
  font-size: 14px;
  line-height: 1.6;
}

.compact-form {
  margin-bottom: 0;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.full-width {
  width: 100%;
}

@media (max-width: 1180px) {
  .location-card-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {
  .residence-card-grid,
  .location-card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .resource-tab-actions {
    grid-column: 1 / -1;
    grid-row: auto;
    flex-wrap: wrap;
    justify-content: flex-start;
    justify-self: start;
    margin-bottom: 12px;
    margin-left: 0;
    margin-top: 0;
  }

  .resource-tabs {
    grid-row: auto;
  }
}

@media (max-width: 680px) {
  .residence-card-grid,
  .location-card-grid,
  .form-row {
    grid-template-columns: 1fr;
  }

  .resource-detail-shell {
    padding-inline: 0;
  }

  .card-cover {
    min-height: 180px;
  }

  .detail-cover {
    min-height: 220px;
  }

  .toolbar-select {
    width: 100%;
  }
}
</style>
