<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, type FormInstance } from 'element-plus'
import { CirclePlus, Edit, Plus } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../../api/client'
import type { AttributeDefinition, AttributeOption, Category } from '../../api/configuration'
import { useConfigurationStore } from '../../stores/configuration'

interface CategoryOption {
  id: number
  label: string
}

const configuration = useConfigurationStore()
const { data } = storeToRefs(configuration)

const categoryFormRef = ref<FormInstance>()
const fieldFormRef = ref<FormInstance>()
const categoryEditFormRef = ref<FormInstance>()
const fieldEditFormRef = ref<FormInstance>()
const optionFormRef = ref<FormInstance>()
const optionEditFormRef = ref<FormInstance>()
const categoryEditOpen = ref(false)
const fieldEditOpen = ref(false)
const optionEditOpen = ref(false)
const editingCategory = ref<Category | null>(null)
const editingField = ref<AttributeDefinition | null>(null)
const editingOption = ref<AttributeOption | null>(null)
const categorySaving = ref(false)
const fieldSaving = ref(false)
const categoryEditSaving = ref(false)
const fieldEditSaving = ref(false)
const optionSaving = ref(false)
const optionEditSaving = ref(false)

const categoryForm = reactive({
  code: '',
  name: '',
  icon: '',
  parent_id: null as number | null
})

const categoryEditForm = reactive({
  parent_id: null as number | null,
  name: '',
  icon: '',
  sort_order: 0,
  is_active: true
})

const fieldForm = reactive({
  category_id: undefined as number | undefined,
  key: '',
  name: '',
  field_type: 'text',
  is_required: false,
  is_filterable: false
})

const fieldEditForm = reactive({
  name: '',
  field_type: 'text',
  default_value: '',
  privacy_level: 'normal',
  is_required: false,
  is_filterable: false,
  sort_order: 0,
  is_active: true
})

const optionForm = reactive({
  definition_id: undefined as number | undefined,
  label: '',
  value: '',
  sort_order: 0
})

const optionEditForm = reactive({
  label: '',
  sort_order: 0,
  is_active: true
})

const fieldTypes = [
  'text',
  'long_text',
  'number',
  'money',
  'date',
  'datetime',
  'single_select',
  'multi_select',
  'boolean',
  'url',
  'attachment',
  'encrypted_text',
  'reminder_date'
]

const selectFieldTypes = new Set(['single_select', 'multi_select'])

const categories = computed(() => data.value?.categories ?? [])
const categoryOptions = computed<CategoryOption[]>(() => flattenCategoryOptions(categories.value))
const selectedCategory = computed(() =>
  fieldForm.category_id ? findCategory(categories.value, fieldForm.category_id) : null
)
const selectedCategoryFields = computed(() => selectedCategory.value?.attribute_definitions ?? [])
const selectableAttributeDefinitions = computed(() =>
  selectedCategoryFields.value.filter((field) => selectFieldTypes.has(field.field_type))
)
const selectedOptionDefinitionIsValid = computed(() => isOptionDefinitionSelectable(optionForm.definition_id))
const optionCreateDisabled = computed(() => !selectedOptionDefinitionIsValid.value)
const categoryEditParentOptions = computed<CategoryOption[]>(() =>
  flattenCategoryOptions(
    categories.value,
    editingCategory.value ? collectCategoryIds(editingCategory.value) : new Set<number>()
  )
)
const fieldEmptyText = computed(() => (selectedCategory.value ? '暂无字段' : '请选择分类'))

watch(selectableAttributeDefinitions, (fields) => {
  if (optionForm.definition_id && !fields.some((field) => field.id === optionForm.definition_id)) {
    optionForm.definition_id = undefined
  }
})

function isOptionDefinitionSelectable(definitionId: number | undefined): boolean {
  return selectableAttributeDefinitions.value.some((field) => field.id === definitionId)
}

function collectCategoryIds(category: Category): Set<number> {
  const ids = new Set<number>([category.id])
  for (const child of category.children ?? []) {
    for (const childId of collectCategoryIds(child)) {
      ids.add(childId)
    }
  }
  return ids
}

function flattenCategoryOptions(nodes: Category[], excludedIds = new Set<number>(), depth = 0): CategoryOption[] {
  return nodes.flatMap((node) => {
    if (excludedIds.has(node.id)) return []
    return [
      { id: node.id, label: `${'  '.repeat(depth)}${node.name}` },
      ...flattenCategoryOptions(node.children ?? [], excludedIds, depth + 1)
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

async function validateForm(form?: FormInstance) {
  if (!form) return false
  return form.validate().then(() => true).catch(() => false)
}

function trimCategoryForm() {
  categoryForm.code = categoryForm.code.trim()
  categoryForm.name = categoryForm.name.trim()
  categoryForm.icon = categoryForm.icon.trim()
}

function trimCategoryEditForm() {
  categoryEditForm.name = categoryEditForm.name.trim()
  categoryEditForm.icon = categoryEditForm.icon.trim()
}

function trimFieldForm() {
  fieldForm.key = fieldForm.key.trim()
  fieldForm.name = fieldForm.name.trim()
}

function trimFieldEditForm() {
  fieldEditForm.name = fieldEditForm.name.trim()
  fieldEditForm.default_value = fieldEditForm.default_value.trim()
  fieldEditForm.privacy_level = fieldEditForm.privacy_level.trim()
}

function trimOptionForm() {
  optionForm.label = optionForm.label.trim()
  optionForm.value = optionForm.value.trim()
}

function trimOptionEditForm() {
  optionEditForm.label = optionEditForm.label.trim()
}

async function saveCategory() {
  trimCategoryForm()
  const valid = await validateForm(categoryFormRef.value)
  if (!valid) return

  categorySaving.value = true
  try {
    await configuration.createCategory({
      parent_id: categoryForm.parent_id,
      code: categoryForm.code.trim(),
      name: categoryForm.name.trim(),
      icon: categoryForm.icon.trim()
    })
    Object.assign(categoryForm, { code: '', name: '', icon: '', parent_id: null })
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    categorySaving.value = false
  }
}

function openCategoryEdit(category: Category) {
  editingCategory.value = category
  Object.assign(categoryEditForm, {
    parent_id: category.parent_id,
    name: category.name,
    icon: category.icon,
    sort_order: category.sort_order,
    is_active: category.is_active
  })
  categoryEditOpen.value = true
}

function clearCategoryEdit() {
  editingCategory.value = null
  Object.assign(categoryEditForm, {
    parent_id: null,
    name: '',
    icon: '',
    sort_order: 0,
    is_active: true
  })
}

async function updateCategory() {
  trimCategoryEditForm()
  const valid = await validateForm(categoryEditFormRef.value)
  if (!valid || !editingCategory.value) return

  categoryEditSaving.value = true
  try {
    await configuration.updateCategory(editingCategory.value.id, {
      parent_id: categoryEditForm.parent_id,
      name: categoryEditForm.name.trim(),
      icon: categoryEditForm.icon.trim(),
      sort_order: Number(categoryEditForm.sort_order) || 0,
      is_active: categoryEditForm.is_active
    })
    categoryEditOpen.value = false
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    categoryEditSaving.value = false
  }
}

async function saveField() {
  trimFieldForm()
  const valid = await validateForm(fieldFormRef.value)
  if (!valid) return
  if (!fieldForm.category_id) return

  fieldSaving.value = true
  try {
    await configuration.createAttributeDefinition({
      category_id: fieldForm.category_id,
      key: fieldForm.key.trim(),
      name: fieldForm.name.trim(),
      field_type: fieldForm.field_type,
      is_required: fieldForm.is_required,
      is_filterable: fieldForm.is_filterable
    })
    Object.assign(fieldForm, {
      key: '',
      name: '',
      field_type: 'text',
      is_required: false,
      is_filterable: false
    })
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    fieldSaving.value = false
  }
}

function openFieldEdit(field: AttributeDefinition) {
  editingField.value = field
  Object.assign(fieldEditForm, {
    name: field.name,
    field_type: field.field_type,
    default_value: field.default_value,
    privacy_level: field.privacy_level,
    is_required: field.is_required,
    is_filterable: field.is_filterable,
    sort_order: field.sort_order,
    is_active: field.is_active
  })
  fieldEditOpen.value = true
}

function clearFieldEdit() {
  editingField.value = null
  Object.assign(fieldEditForm, {
    name: '',
    field_type: 'text',
    default_value: '',
    privacy_level: 'normal',
    is_required: false,
    is_filterable: false,
    sort_order: 0,
    is_active: true
  })
}

async function updateAttributeDefinition() {
  trimFieldEditForm()
  const valid = await validateForm(fieldEditFormRef.value)
  if (!valid || !editingField.value) return

  fieldEditSaving.value = true
  try {
    await configuration.updateAttributeDefinition(editingField.value.id, {
      name: fieldEditForm.name.trim(),
      field_type: fieldEditForm.field_type,
      default_value: fieldEditForm.default_value.trim(),
      privacy_level: fieldEditForm.privacy_level.trim() || 'normal',
      is_required: fieldEditForm.is_required,
      is_filterable: fieldEditForm.is_filterable,
      sort_order: Number(fieldEditForm.sort_order) || 0,
      is_active: fieldEditForm.is_active
    })
    fieldEditOpen.value = false
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    fieldEditSaving.value = false
  }
}

function openOptionEdit(option: AttributeOption) {
  editingOption.value = option
  Object.assign(optionEditForm, {
    label: option.label,
    sort_order: option.sort_order,
    is_active: option.is_active
  })
  optionEditOpen.value = true
}

function clearOptionEdit() {
  editingOption.value = null
  Object.assign(optionEditForm, {
    label: '',
    sort_order: 0,
    is_active: true
  })
}

async function saveAttributeOption() {
  trimOptionForm()
  const valid = await validateForm(optionFormRef.value)
  if (!valid || !optionForm.definition_id || !isOptionDefinitionSelectable(optionForm.definition_id)) return

  optionSaving.value = true
  try {
    await configuration.createAttributeOption({
      definition_id: optionForm.definition_id,
      label: optionForm.label.trim(),
      value: optionForm.value.trim(),
      sort_order: Number(optionForm.sort_order) || 0
    })
    Object.assign(optionForm, { label: '', value: '', sort_order: 0 })
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    optionSaving.value = false
  }
}

async function updateAttributeOption() {
  trimOptionEditForm()
  const valid = await validateForm(optionEditFormRef.value)
  if (!valid || !editingOption.value) return

  optionEditSaving.value = true
  try {
    await configuration.updateAttributeOption(editingOption.value.id, {
      label: optionEditForm.label.trim(),
      sort_order: Number(optionEditForm.sort_order) || 0,
      is_active: optionEditForm.is_active
    })
    optionEditOpen.value = false
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    optionEditSaving.value = false
  }
}
</script>

<template>
  <div class="panel-grid two-columns">
    <section class="tool-section">
      <h2>分类</h2>
      <el-form
        ref="categoryFormRef"
        :model="categoryForm"
        label-position="top"
        class="compact-form"
      >
        <div class="form-row">
          <el-form-item label="编码" prop="code" :rules="[{ required: true, message: '请输入编码' }]">
            <el-input v-model="categoryForm.code" maxlength="50" />
          </el-form-item>
          <el-form-item label="名称" prop="name" :rules="[{ required: true, message: '请输入名称' }]">
            <el-input v-model="categoryForm.name" maxlength="50" />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="图标">
            <el-input v-model="categoryForm.icon" maxlength="50" />
          </el-form-item>
          <el-form-item label="上级分类">
            <el-select v-model="categoryForm.parent_id" class="full-width" clearable>
              <el-option
                v-for="category in categoryOptions"
                :key="category.id"
                :label="category.label"
                :value="category.id"
              />
            </el-select>
          </el-form-item>
        </div>
        <el-button type="primary" :icon="Plus" :loading="categorySaving" @click="saveCategory">
          保存分类
        </el-button>
      </el-form>

      <el-table
        :data="categories"
        row-key="id"
        size="small"
        class="data-table"
        default-expand-all
      >
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="code" label="编码" min-width="140" show-overflow-tooltip />
        <el-table-column prop="icon" label="图标" min-width="100" />
        <el-table-column prop="is_active" label="状态" width="92">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="92" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" :icon="Edit" @click="openCategoryEdit(row)">
              编辑
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="tool-section">
      <h2>字段</h2>
      <el-form ref="fieldFormRef" :model="fieldForm" label-position="top" class="compact-form">
        <el-form-item
          label="所属分类"
          prop="category_id"
          :rules="[{ required: true, message: '请选择分类' }]"
        >
          <el-select v-model="fieldForm.category_id" class="full-width">
            <el-option
              v-for="category in categoryOptions"
              :key="category.id"
              :label="category.label"
              :value="category.id"
            />
          </el-select>
        </el-form-item>
        <div class="form-row">
          <el-form-item label="字段键" prop="key" :rules="[{ required: true, message: '请输入字段键' }]">
            <el-input v-model="fieldForm.key" maxlength="50" />
          </el-form-item>
          <el-form-item label="字段名称" prop="name" :rules="[{ required: true, message: '请输入字段名称' }]">
            <el-input v-model="fieldForm.name" maxlength="50" />
          </el-form-item>
        </div>
        <el-form-item
          label="字段类型"
          prop="field_type"
          :rules="[{ required: true, message: '请选择字段类型' }]"
        >
          <el-select v-model="fieldForm.field_type" class="full-width">
            <el-option v-for="type in fieldTypes" :key="type" :label="type" :value="type" />
          </el-select>
        </el-form-item>
        <div class="switch-row">
          <el-checkbox v-model="fieldForm.is_required">必填</el-checkbox>
          <el-checkbox v-model="fieldForm.is_filterable">可筛选</el-checkbox>
        </div>
        <el-button type="primary" :icon="CirclePlus" :loading="fieldSaving" @click="saveField">
          保存字段
        </el-button>
      </el-form>

      <h3 class="subsection-title">已有字段</h3>
      <el-table
        :data="selectedCategoryFields"
        size="small"
        class="data-table"
        :empty-text="fieldEmptyText"
      >
        <el-table-column type="expand" width="42">
          <template #default="{ row }">
            <div class="nested-options">
              <el-table :data="row.options ?? []" size="small" empty-text="暂无选项">
                <el-table-column prop="label" label="选项" min-width="140" />
                <el-table-column prop="value" label="值" min-width="140" show-overflow-tooltip />
                <el-table-column prop="is_active" label="状态" width="92">
                  <template #default="{ row: option }">
                    <el-tag size="small" :type="option.is_active ? 'success' : 'info'">
                      {{ option.is_active ? '启用' : '停用' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="92" fixed="right">
                  <template #default="{ row: option }">
                    <el-button text type="primary" :icon="Edit" @click="openOptionEdit(option)">
                      编辑
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="字段" min-width="120" />
        <el-table-column prop="key" label="键" min-width="120" show-overflow-tooltip />
        <el-table-column prop="field_type" label="类型" min-width="120" />
        <el-table-column prop="is_required" label="必填" width="74">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_required ? 'warning' : 'info'">
              {{ row.is_required ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_filterable" label="筛选" width="74">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_filterable ? 'success' : 'info'">
              {{ row.is_filterable ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="92">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="92" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" :icon="Edit" @click="openFieldEdit(row)">
              编辑
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-form
        ref="optionFormRef"
        :model="optionForm"
        label-position="top"
        class="compact-form option-form"
      >
        <h3 class="subsection-title">新增字段选项</h3>
        <el-form-item
          label="选择字段"
          prop="definition_id"
          :rules="[{ required: true, message: '请选择字段' }]"
        >
          <el-select
            v-model="optionForm.definition_id"
            class="full-width"
            :disabled="selectableAttributeDefinitions.length === 0"
            placeholder="仅支持单选和多选字段"
          >
            <el-option
              v-for="field in selectableAttributeDefinitions"
              :key="field.id"
              :label="field.name"
              :value="field.id"
            />
          </el-select>
        </el-form-item>
        <div class="form-row">
          <el-form-item label="选项名称" prop="label" :rules="[{ required: true, message: '请输入选项名称' }]">
            <el-input v-model="optionForm.label" maxlength="80" :disabled="optionCreateDisabled" />
          </el-form-item>
          <el-form-item label="选项值" prop="value" :rules="[{ required: true, message: '请输入选项值' }]">
            <el-input v-model="optionForm.value" maxlength="80" :disabled="optionCreateDisabled" />
          </el-form-item>
        </div>
        <el-form-item label="排序">
          <el-input-number
            v-model="optionForm.sort_order"
            :min="0"
            :step="1"
            controls-position="right"
            class="full-width"
            :disabled="optionCreateDisabled"
          />
        </el-form-item>
        <el-button
          type="primary"
          :icon="CirclePlus"
          :loading="optionSaving"
          :disabled="optionCreateDisabled"
          @click="saveAttributeOption"
        >
          保存选项
        </el-button>
      </el-form>
    </section>
  </div>

  <el-dialog
    v-model="categoryEditOpen"
    title="编辑分类"
    width="520px"
    destroy-on-close
    @closed="clearCategoryEdit"
  >
    <el-form
      ref="categoryEditFormRef"
      :model="categoryEditForm"
      label-position="top"
      class="compact-form"
    >
      <el-form-item label="上级分类">
        <el-select v-model="categoryEditForm.parent_id" class="full-width" clearable>
          <el-option
            v-for="category in categoryEditParentOptions"
            :key="category.id"
            :label="category.label"
            :value="category.id"
          />
        </el-select>
      </el-form-item>
      <div class="form-row">
        <el-form-item label="名称" prop="name" :rules="[{ required: true, message: '请输入名称' }]">
          <el-input v-model="categoryEditForm.name" maxlength="50" />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="categoryEditForm.icon" maxlength="50" />
        </el-form-item>
      </div>
      <div class="form-row">
        <el-form-item label="排序">
          <el-input-number
            v-model="categoryEditForm.sort_order"
            :min="0"
            :step="1"
            controls-position="right"
            class="full-width"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch
            v-model="categoryEditForm.is_active"
            active-text="启用"
            inactive-text="停用"
          />
        </el-form-item>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="categoryEditOpen = false">取消</el-button>
      <el-button type="primary" :loading="categoryEditSaving" @click="updateCategory">
        保存
      </el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="fieldEditOpen"
    title="编辑字段"
    width="560px"
    destroy-on-close
    @closed="clearFieldEdit"
  >
    <el-form
      ref="fieldEditFormRef"
      :model="fieldEditForm"
      label-position="top"
      class="compact-form"
    >
      <div class="form-row">
        <el-form-item label="字段名称" prop="name" :rules="[{ required: true, message: '请输入字段名称' }]">
          <el-input v-model="fieldEditForm.name" maxlength="50" />
        </el-form-item>
        <el-form-item
          label="字段类型"
          prop="field_type"
          :rules="[{ required: true, message: '请选择字段类型' }]"
        >
          <el-select v-model="fieldEditForm.field_type" class="full-width">
            <el-option v-for="type in fieldTypes" :key="type" :label="type" :value="type" />
          </el-select>
        </el-form-item>
      </div>
      <div class="form-row">
        <el-form-item label="默认值">
          <el-input v-model="fieldEditForm.default_value" maxlength="120" />
        </el-form-item>
        <el-form-item label="隐私级别">
          <el-input v-model="fieldEditForm.privacy_level" maxlength="40" />
        </el-form-item>
      </div>
      <div class="form-row">
        <el-form-item label="排序">
          <el-input-number
            v-model="fieldEditForm.sort_order"
            :min="0"
            :step="1"
            controls-position="right"
            class="full-width"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch
            v-model="fieldEditForm.is_active"
            active-text="启用"
            inactive-text="停用"
          />
        </el-form-item>
      </div>
      <div class="switch-row">
        <el-checkbox v-model="fieldEditForm.is_required">必填</el-checkbox>
        <el-checkbox v-model="fieldEditForm.is_filterable">可筛选</el-checkbox>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="fieldEditOpen = false">取消</el-button>
      <el-button type="primary" :loading="fieldEditSaving" @click="updateAttributeDefinition">
        保存
      </el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="optionEditOpen"
    title="编辑字段选项"
    width="480px"
    destroy-on-close
    @closed="clearOptionEdit"
  >
    <el-form
      ref="optionEditFormRef"
      :model="optionEditForm"
      label-position="top"
      class="compact-form"
    >
      <el-form-item label="选项名称" prop="label" :rules="[{ required: true, message: '请输入选项名称' }]">
        <el-input v-model="optionEditForm.label" maxlength="80" />
      </el-form-item>
      <el-form-item label="选项值">
        <el-input :model-value="editingOption?.value" class="readonly-value" readonly disabled />
      </el-form-item>
      <div class="form-row">
        <el-form-item label="排序">
          <el-input-number
            v-model="optionEditForm.sort_order"
            :min="0"
            :step="1"
            controls-position="right"
            class="full-width"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch
            v-model="optionEditForm.is_active"
            active-text="启用"
            inactive-text="停用"
          />
        </el-form-item>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="optionEditOpen = false">取消</el-button>
      <el-button type="primary" :loading="optionEditSaving" @click="updateAttributeOption">
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

.switch-row {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-bottom: 18px;
}

.data-table {
  margin-top: 14px;
}

.subsection-title {
  margin: 18px 0 10px;
  color: #26342e;
  font-size: 14px;
  font-weight: 700;
}

.option-form {
  margin-top: 18px;
}

.nested-options {
  padding: 8px 0 8px 42px;
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
