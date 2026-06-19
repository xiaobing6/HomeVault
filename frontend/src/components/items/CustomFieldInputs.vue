<script setup lang="ts">
import { computed } from 'vue'

import type { AttributeDefinition, AttributeOption } from '../../api/configuration'

const props = defineProps<{
  definitions: AttributeDefinition[]
  modelValue: Record<number, string>
}>()

const emit = defineEmits<{
  'update:modelValue': [value: Record<number, string>]
}>()

const activeDefinitions = computed(() =>
  [...props.definitions]
    .filter((definition) => definition.is_active)
    .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
)

function activeOptions(definition: AttributeDefinition): AttributeOption[] {
  return [...(definition.options ?? [])]
    .filter((option) => option.is_active)
    .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
}

function valueOf(definitionId: number): string {
  return props.modelValue[definitionId] ?? ''
}

function updateValue(definitionId: number, value: string) {
  emit('update:modelValue', {
    ...props.modelValue,
    [definitionId]: value
  })
}

function numberValue(definitionId: number): number | undefined {
  const rawValue = valueOf(definitionId)
  if (rawValue.trim() === '') return undefined
  const parsedValue = Number(rawValue)
  return Number.isFinite(parsedValue) ? parsedValue : undefined
}

function booleanValue(definitionId: number): boolean {
  return valueOf(definitionId).trim().toLowerCase() === 'true'
}

function multiSelectValue(definitionId: number): string[] {
  const rawValue = valueOf(definitionId).trim()
  if (!rawValue) return []
  if (rawValue.startsWith('[')) {
    try {
      const parsedValue = JSON.parse(rawValue) as unknown
      if (Array.isArray(parsedValue)) {
        return parsedValue.filter((item): item is string => typeof item === 'string')
      }
    } catch {
      return []
    }
  }
  return rawValue.split(',').map((item) => item.trim()).filter(Boolean)
}
</script>

<template>
  <el-empty v-if="activeDefinitions.length === 0" description="这个分类暂无自定义字段" />

  <div v-else class="custom-field-list">
    <el-form-item
      v-for="definition in activeDefinitions"
      :key="definition.id"
      :label="definition.name"
      :required="definition.is_required"
    >
      <el-input
        v-if="['text', 'encrypted_text', 'url'].includes(definition.field_type)"
        :model-value="valueOf(definition.id)"
        :maxlength="definition.field_type === 'url' ? 500 : 240"
        clearable
        @update:model-value="(value: string) => updateValue(definition.id, value)"
      />

      <el-input
        v-else-if="definition.field_type === 'long_text'"
        :model-value="valueOf(definition.id)"
        type="textarea"
        :rows="4"
        maxlength="1000"
        show-word-limit
        @update:model-value="(value: string) => updateValue(definition.id, value)"
      />

      <el-input-number
        v-else-if="['number', 'money'].includes(definition.field_type)"
        :model-value="numberValue(definition.id)"
        class="full-width"
        :precision="definition.field_type === 'money' ? 2 : undefined"
        :controls-position="'right'"
        @update:model-value="(value: number | undefined) => updateValue(definition.id, value == null ? '' : String(value))"
      />

      <el-date-picker
        v-else-if="definition.field_type === 'date' || definition.field_type === 'reminder_date'"
        :model-value="valueOf(definition.id)"
        class="full-width"
        type="date"
        value-format="YYYY-MM-DD"
        placeholder="选择日期"
        @update:model-value="(value: string | null) => updateValue(definition.id, value ?? '')"
      />

      <el-date-picker
        v-else-if="definition.field_type === 'datetime'"
        :model-value="valueOf(definition.id)"
        class="full-width"
        type="datetime"
        format="YYYY-MM-DD HH:mm"
        value-format="YYYY-MM-DDTHH:mm:ss"
        placeholder="选择时间"
        @update:model-value="(value: string | null) => updateValue(definition.id, value ?? '')"
      />

      <el-select
        v-else-if="definition.field_type === 'single_select'"
        :model-value="valueOf(definition.id)"
        class="full-width"
        clearable
        placeholder="请选择"
        @update:model-value="(value: string) => updateValue(definition.id, value ?? '')"
      >
        <el-option
          v-for="option in activeOptions(definition)"
          :key="option.id"
          :label="option.label"
          :value="option.value"
        />
      </el-select>

      <el-select
        v-else-if="definition.field_type === 'multi_select'"
        :model-value="multiSelectValue(definition.id)"
        class="full-width"
        multiple
        clearable
        collapse-tags
        collapse-tags-tooltip
        placeholder="请选择"
        @update:model-value="(value: string[]) => updateValue(definition.id, value.join(','))"
      >
        <el-option
          v-for="option in activeOptions(definition)"
          :key="option.id"
          :label="option.label"
          :value="option.value"
        />
      </el-select>

      <el-switch
        v-else-if="definition.field_type === 'boolean'"
        :model-value="booleanValue(definition.id)"
        active-text="是"
        inactive-text="否"
        @update:model-value="(value: boolean) => updateValue(definition.id, value ? 'true' : 'false')"
      />

      <el-alert
        v-else-if="definition.field_type === 'attachment'"
        title="请在图片和附件步骤上传"
        type="info"
        :closable="false"
      />

      <el-input
        v-else
        :model-value="valueOf(definition.id)"
        clearable
        @update:model-value="(value: string) => updateValue(definition.id, value)"
      />
    </el-form-item>
  </div>
</template>

<style scoped>
.custom-field-list {
  display: grid;
  gap: 6px;
}

.full-width {
  width: 100%;
}
</style>
