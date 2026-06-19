<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, type FormInstance } from 'element-plus'
import { CirclePlus, Plus } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../../api/client'
import type { Category } from '../../api/configuration'
import { useConfigurationStore } from '../../stores/configuration'

interface CategoryOption {
  id: number
  label: string
}

const configuration = useConfigurationStore()
const { data } = storeToRefs(configuration)

const categoryFormRef = ref<FormInstance>()
const fieldFormRef = ref<FormInstance>()
const categorySaving = ref(false)
const fieldSaving = ref(false)

const categoryForm = reactive({
  code: '',
  name: '',
  icon: '',
  parent_id: null as number | null
})

const fieldForm = reactive({
  category_id: undefined as number | undefined,
  key: '',
  name: '',
  field_type: 'text',
  is_required: false,
  is_filterable: false
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

const categories = computed(() => data.value?.categories ?? [])
const categoryOptions = computed<CategoryOption[]>(() => flattenCategories(categories.value))

function flattenCategories(nodes: Category[], depth = 0): CategoryOption[] {
  return nodes.flatMap((node) => [
    { id: node.id, label: `${'　'.repeat(depth)}${node.name}` },
    ...flattenCategories(node.children ?? [], depth + 1)
  ])
}

async function saveCategory() {
  if (!categoryFormRef.value) return
  await categoryFormRef.value.validate()

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

async function saveField() {
  if (!fieldFormRef.value) return
  await fieldFormRef.value.validate()
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
    </section>
  </div>
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
  gap: 18px;
  margin-bottom: 18px;
}

.data-table {
  margin-top: 14px;
}

@media (max-width: 960px) {
  .two-columns,
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
