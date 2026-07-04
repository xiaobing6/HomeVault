<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { Delete, Edit, Plus } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../../api/client'
import type { FamilyMember } from '../../api/configuration'
import { useConfigurationStore } from '../../stores/configuration'

const configuration = useConfigurationStore()
const { data } = storeToRefs(configuration)

const formRef = ref<FormInstance>()
const memberEditFormRef = ref<FormInstance>()
const memberEditOpen = ref(false)
const editingMember = ref<FamilyMember | null>(null)
const saving = ref(false)
const memberEditSaving = ref(false)
const deletingMemberId = ref<number | null>(null)
const form = reactive({
  name: '',
  relation: '',
  phone: '',
  note: ''
})

const memberEditForm = reactive({
  name: '',
  relation: '',
  phone: '',
  note: '',
  is_active: true
})

const members = computed(() => data.value?.family_members ?? [])

async function validateForm(form?: FormInstance) {
  if (!form) return false
  return form.validate().then(() => true).catch(() => false)
}

function trimMemberForm() {
  form.name = form.name.trim()
  form.relation = form.relation.trim()
  form.phone = form.phone.trim()
  form.note = form.note.trim()
}

function trimMemberEditForm() {
  memberEditForm.name = memberEditForm.name.trim()
  memberEditForm.relation = memberEditForm.relation.trim()
  memberEditForm.phone = memberEditForm.phone.trim()
  memberEditForm.note = memberEditForm.note.trim()
}

async function saveMember() {
  trimMemberForm()
  const valid = await validateForm(formRef.value)
  if (!valid) return

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

function openMemberEdit(member: FamilyMember) {
  editingMember.value = member
  Object.assign(memberEditForm, {
    name: member.name,
    relation: member.relation,
    phone: member.phone,
    note: member.note,
    is_active: member.is_active
  })
  memberEditOpen.value = true
}

function clearMemberEdit() {
  editingMember.value = null
  Object.assign(memberEditForm, {
    name: '',
    relation: '',
    phone: '',
    note: '',
    is_active: true
  })
}

async function updateFamilyMember() {
  trimMemberEditForm()
  const valid = await validateForm(memberEditFormRef.value)
  if (!valid || !editingMember.value) return

  memberEditSaving.value = true
  try {
    await configuration.updateFamilyMember(editingMember.value.id, {
      name: memberEditForm.name.trim(),
      relation: memberEditForm.relation.trim(),
      phone: memberEditForm.phone.trim(),
      note: memberEditForm.note.trim(),
      is_active: memberEditForm.is_active
    })
    memberEditOpen.value = false
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    memberEditSaving.value = false
  }
}

async function confirmDeleteMember(member: FamilyMember) {
  try {
    await ElMessageBox.confirm(
      `确定删除家庭成员「${member.name}」吗？历史记录仍会保留姓名。`,
      '删除家庭成员',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  deletingMemberId.value = member.id
  try {
    await configuration.deleteFamilyMember(member.id)
    ElMessage.success('已删除成员')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    deletingMemberId.value = null
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
        <el-table-column prop="is_active" label="状态" width="92">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" :icon="Edit" @click="openMemberEdit(row)">
              编辑
            </el-button>
            <el-button
              text
              type="danger"
              :icon="Delete"
              :loading="deletingMemberId === row.id"
              @click="confirmDeleteMember(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>

  <el-dialog
    v-model="memberEditOpen"
    title="编辑家庭成员"
    width="520px"
    destroy-on-close
    @closed="clearMemberEdit"
  >
    <el-form
      ref="memberEditFormRef"
      :model="memberEditForm"
      label-position="top"
      class="compact-form"
    >
      <el-form-item label="姓名" prop="name" :rules="[{ required: true, message: '请输入姓名' }]">
        <el-input v-model="memberEditForm.name" maxlength="40" />
      </el-form-item>
      <div class="form-row">
        <el-form-item label="关系">
          <el-input v-model="memberEditForm.relation" maxlength="40" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="memberEditForm.phone" maxlength="40" />
        </el-form-item>
      </div>
      <el-form-item label="备注">
        <el-input v-model="memberEditForm.note" type="textarea" :rows="3" maxlength="120" />
      </el-form-item>
      <el-form-item label="状态">
        <el-switch
          v-model="memberEditForm.is_active"
          active-text="启用"
          inactive-text="停用"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="memberEditOpen = false">取消</el-button>
      <el-button type="primary" :loading="memberEditSaving" @click="updateFamilyMember">
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
