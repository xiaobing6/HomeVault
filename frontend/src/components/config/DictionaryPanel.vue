<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, type FormInstance } from 'element-plus'
import { Edit, Plus } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../../api/client'
import type { DictionaryOption, ItemStatus } from '../../api/configuration'
import { useConfigurationStore } from '../../stores/configuration'

const configuration = useConfigurationStore()
const { data } = storeToRefs(configuration)

const statusFormRef = ref<FormInstance>()
const statusEditFormRef = ref<FormInstance>()
const statusSaving = ref(false)
const statusEditSaving = ref(false)
const statusEditOpen = ref(false)
const editingStatus = ref<ItemStatus | null>(null)
const dictionaryOptionEditFormRef = ref<FormInstance>()
const dictionaryOptionEditOpen = ref(false)
const dictionaryOptionEditSaving = ref(false)
const editingDictionaryOption = ref<DictionaryOption | null>(null)

const statusForm = reactive({
  code: '',
  name: '',
  semantic: 'available',
  sort_order: 0
})

const statusEditForm = reactive({
  name: '',
  semantic: 'available',
  sort_order: 0,
  is_active: true
})

const dictionaryOptionEditForm = reactive({
  label: '',
  sort_order: 0,
  is_active: true
})

const statusSemanticOptions = ['available', 'away', 'removed', 'missing']

const statuses = computed(() => data.value?.item_statuses ?? [])
const dictionaryGroups = computed(() => data.value?.dictionary_groups ?? [])

async function validateForm(form?: FormInstance) {
  if (!form) return false
  return form.validate().then(() => true).catch(() => false)
}

function trimStatusForm() {
  statusForm.code = statusForm.code.trim()
  statusForm.name = statusForm.name.trim()
  statusForm.semantic = statusForm.semantic.trim()
}

function trimStatusEditForm() {
  statusEditForm.name = statusEditForm.name.trim()
  statusEditForm.semantic = statusEditForm.semantic.trim()
}

function openStatusEdit(status: ItemStatus) {
  editingStatus.value = status
  Object.assign(statusEditForm, {
    name: status.name,
    semantic: status.semantic,
    sort_order: status.sort_order,
    is_active: status.is_active
  })
  statusEditOpen.value = true
}

function clearStatusEdit() {
  editingStatus.value = null
  Object.assign(statusEditForm, {
    name: '',
    semantic: 'available',
    sort_order: 0,
    is_active: true
  })
}

function openDictionaryOptionEdit(option: DictionaryOption) {
  editingDictionaryOption.value = option
  Object.assign(dictionaryOptionEditForm, {
    label: option.label,
    sort_order: option.sort_order,
    is_active: option.is_active
  })
  dictionaryOptionEditOpen.value = true
}

function clearDictionaryOptionEdit() {
  editingDictionaryOption.value = null
  Object.assign(dictionaryOptionEditForm, { label: '', sort_order: 0, is_active: true })
}

async function saveItemStatus() {
  trimStatusForm()
  const valid = await validateForm(statusFormRef.value)
  if (!valid) return

  statusSaving.value = true
  try {
    await configuration.createItemStatus({
      code: statusForm.code.trim(),
      name: statusForm.name.trim(),
      semantic: statusForm.semantic.trim(),
      sort_order: Number(statusForm.sort_order) || 0
    })
    Object.assign(statusForm, { code: '', name: '', semantic: 'available', sort_order: 0 })
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    statusSaving.value = false
  }
}

async function updateItemStatus() {
  trimStatusEditForm()
  const valid = await validateForm(statusEditFormRef.value)
  if (!valid || !editingStatus.value) return

  statusEditSaving.value = true
  try {
    await configuration.updateItemStatus(editingStatus.value.id, {
      name: statusEditForm.name.trim(),
      semantic: statusEditForm.semantic.trim(),
      sort_order: Number(statusEditForm.sort_order) || 0,
      is_active: statusEditForm.is_active
    })
    statusEditOpen.value = false
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    statusEditSaving.value = false
  }
}

async function updateDictionaryOption() {
  dictionaryOptionEditForm.label = dictionaryOptionEditForm.label.trim()
  const valid = await validateForm(dictionaryOptionEditFormRef.value)
  if (!valid || !editingDictionaryOption.value) return

  dictionaryOptionEditSaving.value = true
  try {
    await configuration.updateDictionaryOption(editingDictionaryOption.value.id, {
      label: dictionaryOptionEditForm.label,
      sort_order: Number(dictionaryOptionEditForm.sort_order) || 0,
      is_active: dictionaryOptionEditForm.is_active
    })
    dictionaryOptionEditOpen.value = false
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    dictionaryOptionEditSaving.value = false
  }
}
</script>

<template>
  <div class="panel-grid two-columns">
    <section class="tool-section">
      <h2>物品状态</h2>
      <el-form
        ref="statusFormRef"
        :model="statusForm"
        label-position="top"
        class="compact-form"
      >
        <div class="form-row">
          <el-form-item label="编码" prop="code" :rules="[{ required: true, message: '请输入编码' }]">
            <el-input v-model="statusForm.code" maxlength="50" />
          </el-form-item>
          <el-form-item label="名称" prop="name" :rules="[{ required: true, message: '请输入名称' }]">
            <el-input v-model="statusForm.name" maxlength="50" />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item
            label="语义"
            prop="semantic"
            :rules="[{ required: true, message: '请选择语义' }]"
          >
            <el-select v-model="statusForm.semantic" class="full-width">
              <el-option
                v-for="semantic in statusSemanticOptions"
                :key="semantic"
                :label="semantic"
                :value="semantic"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="排序">
            <el-input-number
              v-model="statusForm.sort_order"
              :min="0"
              :step="1"
              controls-position="right"
              class="full-width"
            />
          </el-form-item>
        </div>
        <el-button type="primary" :icon="Plus" :loading="statusSaving" @click="saveItemStatus">
          保存状态
        </el-button>
      </el-form>

      <el-table :data="statuses" size="small" class="data-table">
        <el-table-column prop="name" label="名称" min-width="120" />
        <el-table-column prop="code" label="编码" min-width="140" />
        <el-table-column prop="semantic" label="语义" min-width="120" />
        <el-table-column prop="is_active" label="状态" width="92">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_system" label="系统" width="86">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_system ? 'info' : 'success'">
              {{ row.is_system ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="92" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" :icon="Edit" @click="openStatusEdit(row)">
              编辑
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="tool-section">
      <h2>字典</h2>
      <el-table
        :data="dictionaryGroups"
        row-key="id"
        size="small"
        class="data-table"
        default-expand-all
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <el-table :data="row.options" size="small" class="nested-table">
              <el-table-column prop="label" label="选项" min-width="140" />
              <el-table-column prop="value" label="值" min-width="140" />
              <el-table-column prop="sort_order" label="排序" width="86" />
              <el-table-column prop="is_active" label="启用" width="86">
                <template #default="{ row: option }">
                  <el-tag size="small" :type="option.is_active ? 'success' : 'info'">
                    {{ option.is_active ? '是' : '否' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="92" fixed="right">
                <template #default="{ row: option }">
                  <el-button text type="primary" :icon="Edit" @click="openDictionaryOptionEdit(option)">
                    编辑
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="code" label="编码" min-width="160" show-overflow-tooltip />
        <el-table-column prop="is_system" label="系统" width="86">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_system ? 'info' : 'success'">
              {{ row.is_system ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>

  <el-dialog
    v-model="statusEditOpen"
    title="编辑物品状态"
    width="520px"
    destroy-on-close
    @closed="clearStatusEdit"
  >
    <el-form
      ref="statusEditFormRef"
      :model="statusEditForm"
      label-position="top"
      class="compact-form"
    >
      <el-form-item label="编码">
        <el-input :model-value="editingStatus?.code" class="readonly-value" readonly disabled />
      </el-form-item>
      <div class="form-row">
        <el-form-item label="名称" prop="name" :rules="[{ required: true, message: '请输入名称' }]">
          <el-input v-model="statusEditForm.name" maxlength="50" />
        </el-form-item>
        <el-form-item
          label="语义"
          prop="semantic"
          :rules="[{ required: true, message: '请选择语义' }]"
        >
          <el-select v-model="statusEditForm.semantic" class="full-width">
            <el-option
              v-for="semantic in statusSemanticOptions"
              :key="semantic"
              :label="semantic"
              :value="semantic"
            />
          </el-select>
        </el-form-item>
      </div>
      <div class="form-row">
        <el-form-item label="排序">
          <el-input-number
            v-model="statusEditForm.sort_order"
            :min="0"
            :step="1"
            controls-position="right"
            class="full-width"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch
            v-model="statusEditForm.is_active"
            active-text="启用"
            inactive-text="停用"
          />
        </el-form-item>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="statusEditOpen = false">取消</el-button>
      <el-button type="primary" :loading="statusEditSaving" @click="updateItemStatus">
        保存
      </el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="dictionaryOptionEditOpen"
    title="编辑字典选项"
    width="520px"
    destroy-on-close
    @closed="clearDictionaryOptionEdit"
  >
    <el-form
      ref="dictionaryOptionEditFormRef"
      :model="dictionaryOptionEditForm"
      label-position="top"
      class="compact-form"
    >
      <el-form-item label="值">
        <el-input :model-value="editingDictionaryOption?.value" class="readonly-value" readonly disabled />
      </el-form-item>
      <div class="form-row">
        <el-form-item label="选项" prop="label" :rules="[{ required: true, message: '请输入选项' }]">
          <el-input v-model="dictionaryOptionEditForm.label" maxlength="80" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number
            v-model="dictionaryOptionEditForm.sort_order"
            :min="0"
            :step="1"
            controls-position="right"
            class="full-width"
          />
        </el-form-item>
      </div>
      <el-form-item label="状态">
        <el-switch
          v-model="dictionaryOptionEditForm.is_active"
          active-text="启用"
          inactive-text="停用"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dictionaryOptionEditOpen = false">取消</el-button>
      <el-button type="primary" :loading="dictionaryOptionEditSaving" @click="updateDictionaryOption">
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

.data-table {
  margin-top: 14px;
}

.nested-table {
  width: calc(100% - 20px);
  margin-left: 20px;
}

.readonly-value {
  width: 100%;
}

@media (max-width: 960px) {
  .two-columns,
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
