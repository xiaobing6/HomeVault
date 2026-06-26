<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'

import type {
  ReminderCreateRequest,
  ReminderDetail,
  ReminderPriority,
  ReminderUpdateRequest
} from '../../api/reminders'

const props = defineProps<{
  modelValue: boolean
  reminder?: ReminderDetail | null
  saving?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [payload: ReminderCreateRequest | ReminderUpdateRequest]
}>()

interface ReminderFormModel {
  title: string
  description: string
  item_id: number | null
  due_date: string | null
  remind_at: string | null
  priority: ReminderPriority
}

const formRef = ref<FormInstance>()
const form = reactive<ReminderFormModel>({
  title: '',
  description: '',
  item_id: null,
  due_date: null,
  remind_at: null,
  priority: 'normal'
})

const isEditing = computed(() => Boolean(props.reminder))
const isLoanReturn = computed(() => props.reminder?.source_type === 'loan_return')
const title = computed(() => (isEditing.value ? '编辑提醒' : '新增提醒'))

const rules: FormRules<ReminderFormModel> = {
  title: [
    {
      validator: (_rule, value: string, callback) => {
        if (!value.trim()) callback(new Error('请输入提醒标题'))
        else callback()
      },
      trigger: 'blur'
    }
  ]
}

watch(
  () => [props.modelValue, props.reminder] as const,
  ([open]) => {
    if (!open) return
    resetForm()
  },
  { immediate: true }
)

function resetForm() {
  const reminder = props.reminder
  form.title = reminder?.title ?? ''
  form.description = reminder?.description ?? ''
  form.item_id = reminder?.item_id ?? null
  form.due_date = reminder?.due_date ?? null
  form.remind_at = reminder?.remind_at ?? null
  form.priority = reminder?.priority ?? 'normal'
  formRef.value?.clearValidate()
}

function updateOpen(open: boolean) {
  emit('update:modelValue', open)
}

function nullableString(value: string | null): string | null {
  return value && value.trim() ? value : null
}

async function submitForm() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  emit('submit', {
    title: form.title.trim(),
    description: form.description.trim(),
    item_id: form.item_id ?? null,
    due_date: nullableString(form.due_date),
    remind_at: nullableString(form.remind_at),
    priority: form.priority
  })
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    width="min(620px, 96vw)"
    destroy-on-close
    @update:model-value="updateOpen"
  >
    <el-form
      ref="formRef"
      class="reminder-form"
      :model="form"
      :rules="rules"
      label-position="top"
      @submit.prevent
    >
      <el-form-item label="标题" prop="title">
        <el-input v-model="form.title" maxlength="120" show-word-limit />
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
        <el-form-item label="关联物品 ID">
          <el-input-number
            v-model="form.item_id"
            class="full-control"
            :min="1"
            :controls="false"
            :disabled="isLoanReturn"
            placeholder="留空则不关联"
          />
        </el-form-item>

        <el-form-item label="优先级">
          <el-select v-model="form.priority" class="full-control">
            <el-option label="低" value="low" />
            <el-option label="普通" value="normal" />
            <el-option label="高" value="high" />
          </el-select>
        </el-form-item>

        <el-form-item label="到期日期">
          <el-date-picker
            v-model="form.due_date"
            class="full-control"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择到期日期"
            :disabled="isLoanReturn"
            clearable
          />
        </el-form-item>

        <el-form-item label="提醒时间">
          <el-date-picker
            v-model="form.remind_at"
            class="full-control"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="选择提醒时间"
            clearable
          />
        </el-form-item>
      </div>

      <el-alert
        v-if="isLoanReturn"
        type="info"
        :closable="false"
        show-icon
        title="借出归还提醒的关联物品和到期日期由借用流程维护。"
      />
    </el-form>

    <template #footer>
      <el-button @click="updateOpen(false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.reminder-form {
  display: grid;
  gap: 4px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 12px;
}

.full-control {
  width: 100%;
}

@media (max-width: 640px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
