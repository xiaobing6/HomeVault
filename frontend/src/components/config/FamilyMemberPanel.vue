<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, type FormInstance } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../../api/client'
import { useConfigurationStore } from '../../stores/configuration'

const configuration = useConfigurationStore()
const { data } = storeToRefs(configuration)

const formRef = ref<FormInstance>()
const saving = ref(false)
const form = reactive({
  name: '',
  relation: '',
  phone: '',
  note: ''
})

const members = computed(() => data.value?.family_members ?? [])

async function saveMember() {
  if (!formRef.value) return
  await formRef.value.validate()

  saving.value = true
  try {
    await configuration.createFamilyMember({
      name: form.name.trim(),
      relation: form.relation.trim(),
      phone: form.phone.trim(),
      note: form.note.trim()
    })
    Object.assign(form, { name: '', relation: '', phone: '', note: '' })
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="panel-grid">
    <section class="tool-section">
      <h2>家庭成员</h2>
      <el-form ref="formRef" :model="form" label-position="top" class="compact-form">
        <div class="form-row">
          <el-form-item label="姓名" prop="name" :rules="[{ required: true, message: '请输入姓名' }]">
            <el-input v-model="form.name" maxlength="40" />
          </el-form-item>
          <el-form-item label="关系">
            <el-input v-model="form.relation" maxlength="40" />
          </el-form-item>
          <el-form-item label="电话">
            <el-input v-model="form.phone" maxlength="40" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="form.note" maxlength="120" />
          </el-form-item>
        </div>
        <el-button type="primary" :icon="Plus" :loading="saving" @click="saveMember">
          保存成员
        </el-button>
      </el-form>

      <el-table :data="members" size="small" class="data-table">
        <el-table-column prop="name" label="姓名" min-width="120" />
        <el-table-column prop="relation" label="关系" min-width="120" />
        <el-table-column prop="phone" label="电话" min-width="140" />
        <el-table-column prop="note" label="备注" min-width="180" show-overflow-tooltip />
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.panel-grid {
  display: grid;
  gap: 18px;
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
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.data-table {
  margin-top: 14px;
}

@media (max-width: 1040px) {
  .form-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
