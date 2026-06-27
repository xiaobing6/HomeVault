<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Edit, Key, Plus, Refresh, Search } from '@element-plus/icons-vue'

import type {
  AdminUser,
  AdminUserCreateRequest,
  AdminUserFilters,
  AdminUserUpdateRequest
} from '../api/admin'
import { getChineseErrorMessage } from '../api/client'
import { useAdminUsersStore } from '../stores/adminUsers'

type ActiveFilter = '' | 'active' | 'inactive'
type UserDialogMode = 'create' | 'edit'
type ValidationCallback = (error?: Error) => void

interface UserFormModel {
  username: string
  display_name: string
  password: string
  role_codes: string[]
  is_active: boolean
}

interface ResetPasswordFormModel {
  password: string
  confirmPassword: string
}

const adminUsers = useAdminUsersStore()
const { users, roles, total, page, pageSize, loading, saving } = storeToRefs(adminUsers)

const userDialogOpen = ref(false)
const resetPasswordDialogOpen = ref(false)
const userDialogMode = ref<UserDialogMode>('create')
const editingUser = ref<AdminUser | null>(null)
const resettingUser = ref<AdminUser | null>(null)
const userFormRef = ref<FormInstance>()
const resetPasswordFormRef = ref<FormInstance>()
const searchDraft = ref(adminUsers.filters.search ?? '')

const defaultRoleCodes = (): string[] => {
  const viewerRole = roles.value.find((role) => role.code === 'viewer')
  return viewerRole ? [viewerRole.code] : ['viewer']
}

const defaultUserForm = (): UserFormModel => ({
  username: '',
  display_name: '',
  password: '',
  role_codes: defaultRoleCodes(),
  is_active: true
})

const userForm = reactive<UserFormModel>(defaultUserForm())
const resetPasswordForm = reactive<ResetPasswordFormModel>({
  password: '',
  confirmPassword: ''
})

const isCreateMode = computed(() => userDialogMode.value === 'create')
const userDialogTitle = computed(() => (isCreateMode.value ? '新建用户' : '编辑用户'))
const systemRoles = computed(() => roles.value.filter((role) => role.is_system))

const roleValue = computed({
  get: () => adminUsers.filters.role ?? '',
  set: (value: string) => {
    void applyAndLoad({ role: value || null })
  }
})

const activeValue = computed<ActiveFilter>({
  get: () => {
    if (adminUsers.filters.is_active === true) return 'active'
    if (adminUsers.filters.is_active === false) return 'inactive'
    return ''
  },
  set: (value) => {
    void applyAndLoad({
      is_active: value === 'active' ? true : value === 'inactive' ? false : null
    })
  }
})

const userRules: FormRules<UserFormModel> = {
  username: [
    {
      validator: (_rule: unknown, value: string, callback: ValidationCallback) => {
        if (!value.trim()) callback(new Error('请输入用户名'))
        else callback()
      },
      trigger: 'blur'
    }
  ],
  display_name: [
    {
      validator: (_rule: unknown, value: string, callback: ValidationCallback) => {
        if (!value.trim()) callback(new Error('请输入显示名称'))
        else callback()
      },
      trigger: 'blur'
    }
  ],
  password: [
    {
      validator: (_rule: unknown, value: string, callback: ValidationCallback) => {
        if (!isCreateMode.value) {
          callback()
          return
        }
        if (!value) callback(new Error('请输入初始密码'))
        else if (value.length < 8) callback(new Error('初始密码至少 8 位'))
        else callback()
      },
      trigger: 'blur'
    }
  ],
  role_codes: [
    {
      type: 'array',
      required: true,
      min: 1,
      message: '请至少选择一个角色',
      trigger: 'change'
    }
  ]
}

const resetPasswordRules: FormRules<ResetPasswordFormModel> = {
  password: [
    {
      validator: (_rule: unknown, value: string, callback: ValidationCallback) => {
        if (!value) callback(new Error('请输入新密码'))
        else if (value.length < 8) callback(new Error('新密码至少 8 位'))
        else callback()
      },
      trigger: 'blur'
    }
  ],
  confirmPassword: [
    {
      validator: (_rule: unknown, value: string, callback: ValidationCallback) => {
        if (!value) callback(new Error('请再次输入新密码'))
        else if (value !== resetPasswordForm.password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur'
    }
  ]
}

onMounted(async () => {
  syncSearchDraftFromFilters()
  try {
    await Promise.all([adminUsers.loadRoles(), adminUsers.loadUsers()])
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
})

async function validateForm(form?: FormInstance) {
  if (!form) return false
  return form.validate().then(() => true).catch(() => false)
}

async function applyAndLoad(filters: AdminUserFilters) {
  try {
    adminUsers.applyFilters(filters)
    await adminUsers.loadUsers()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

function syncSearchDraftFromFilters() {
  searchDraft.value = adminUsers.filters.search ?? ''
}

function submittedSearch(): string | null {
  const search = searchDraft.value.trim()
  searchDraft.value = search
  return search || null
}

async function loadUsers() {
  try {
    await adminUsers.loadUsers({ search: submittedSearch() })
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function clearSearch() {
  searchDraft.value = ''
  await loadUsers()
}

async function resetFilters() {
  try {
    adminUsers.resetFilters()
    syncSearchDraftFromFilters()
    await adminUsers.loadUsers()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function changePage(nextPage: number) {
  try {
    adminUsers.setPage(nextPage)
    await adminUsers.loadUsers()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function changePageSize(nextSize: number) {
  try {
    adminUsers.setPageSize(nextSize)
    await adminUsers.loadUsers()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

function roleName(roleCode: string): string {
  return roles.value.find((role) => role.code === roleCode)?.name ?? roleCode
}

function activeTagType(isActive: boolean): 'success' | 'info' {
  return isActive ? 'success' : 'info'
}

function formatDateTime(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

async function clearUserValidation() {
  await nextTick()
  userFormRef.value?.clearValidate()
}

async function clearResetPasswordValidation() {
  await nextTick()
  resetPasswordFormRef.value?.clearValidate()
}

function clearUserDialogState() {
  userForm.password = ''
  editingUser.value = null
}

function clearResetPasswordDialogState() {
  resetPasswordForm.password = ''
  resetPasswordForm.confirmPassword = ''
  resettingUser.value = null
}

function openCreateDialog() {
  userDialogMode.value = 'create'
  editingUser.value = null
  Object.assign(userForm, defaultUserForm())
  userDialogOpen.value = true
  void clearUserValidation()
}

function openEditDialog(user: AdminUser) {
  userDialogMode.value = 'edit'
  editingUser.value = user
  Object.assign(userForm, {
    username: user.username,
    display_name: user.display_name,
    password: '',
    role_codes: [...user.roles],
    is_active: user.is_active
  })
  userDialogOpen.value = true
  void clearUserValidation()
}

async function saveUser() {
  const valid = await validateForm(userFormRef.value)
  if (!valid) return

  try {
    if (isCreateMode.value) {
      const payload: AdminUserCreateRequest = {
        username: userForm.username.trim(),
        display_name: userForm.display_name.trim(),
        password: userForm.password,
        role_codes: [...userForm.role_codes]
      }
      await adminUsers.createUser(payload)
      ElMessage.success('用户已创建')
    } else if (editingUser.value) {
      const payload: AdminUserUpdateRequest = {
        display_name: userForm.display_name.trim(),
        is_active: userForm.is_active,
        role_codes: [...userForm.role_codes]
      }
      await adminUsers.updateUser(editingUser.value.id, payload)
      ElMessage.success('用户已更新')
    }

    userDialogOpen.value = false
    clearUserDialogState()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

function openResetPasswordDialog(user: AdminUser) {
  clearResetPasswordDialogState()
  resettingUser.value = user
  resetPasswordDialogOpen.value = true
  void clearResetPasswordValidation()
}

async function saveResetPassword() {
  const valid = await validateForm(resetPasswordFormRef.value)
  if (!valid || !resettingUser.value) return

  const userId = resettingUser.value.id
  const password = resetPasswordForm.password

  try {
    await adminUsers.resetPassword(userId, {
      password
    })
    resetPasswordDialogOpen.value = false
    clearResetPasswordDialogState()
    ElMessage.success('密码已重置')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}
</script>

<template>
  <section class="admin-users-page">
    <div class="page-heading">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-subtitle">集中维护后台账号、角色分配、启停状态和密码重置。</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreateDialog">新建用户</el-button>
    </div>

    <div class="toolbar-panel">
      <el-input
        v-model="searchDraft"
        class="search-input"
        :prefix-icon="Search"
        placeholder="搜索用户名或显示名称"
        clearable
        @keyup.enter="loadUsers"
        @clear="clearSearch"
      />

      <div class="filter-actions">
        <el-select v-model="roleValue" class="filter-select" placeholder="角色">
          <el-option label="全部角色" value="" />
          <el-option v-for="role in roles" :key="role.code" :label="role.name" :value="role.code" />
        </el-select>
        <el-select v-model="activeValue" class="filter-select" placeholder="状态">
          <el-option label="全部状态" value="" />
          <el-option label="启用" value="active" />
          <el-option label="停用" value="inactive" />
        </el-select>
        <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
      </div>
    </div>

    <div class="table-panel">
      <el-table v-loading="loading" :data="users" row-key="id" empty-text="暂无用户">
        <el-table-column prop="username" label="用户名" min-width="150" show-overflow-tooltip />
        <el-table-column prop="display_name" label="显示名称" min-width="150" show-overflow-tooltip />
        <el-table-column label="角色" min-width="200">
          <template #default="{ row }">
            <div class="tag-list">
              <el-tag
                v-for="roleCode in row.roles"
                :key="roleCode"
                size="small"
                effect="plain"
                class="role-tag"
              >
                {{ roleName(roleCode) }}
              </el-tag>
              <span v-if="!row.roles.length" class="muted-text">-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="activeTagType(row.is_active)" effect="plain">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
              <el-button link type="primary" :icon="Key" @click="openResetPasswordDialog(row)">
                重置密码
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pagination-row">
      <el-pagination
        background
        layout="total, sizes, prev, pager, next"
        :total="total"
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[20, 40, 80]"
        @current-change="changePage"
        @size-change="changePageSize"
      />
    </div>

    <div class="roles-panel">
      <div class="panel-heading">
        <h2>系统角色参考</h2>
        <p>查看系统内置角色和权限编码，便于分配账号职责。</p>
      </div>
      <el-table :data="systemRoles" row-key="id" size="small" empty-text="暂无系统角色">
        <el-table-column prop="name" label="名称" min-width="130" />
        <el-table-column prop="code" label="编码" min-width="130" show-overflow-tooltip />
        <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
        <el-table-column label="权限编码" min-width="280">
          <template #default="{ row: role }">
            <div class="tag-list">
              <el-tag
                v-for="permission in role.permissions"
                :key="permission.code"
                size="small"
                effect="plain"
                type="info"
              >
                {{ permission.code }}
              </el-tag>
              <span v-if="!role.permissions.length" class="muted-text">-</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog
      v-model="userDialogOpen"
      :title="userDialogTitle"
      width="min(620px, 96vw)"
      destroy-on-close
      @closed="clearUserDialogState"
    >
      <el-form
        ref="userFormRef"
        :model="userForm"
        :rules="userRules"
        label-position="top"
        class="dialog-form"
        @submit.prevent
      >
        <div class="form-grid">
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="userForm.username"
              maxlength="40"
              :disabled="!isCreateMode"
              autocomplete="off"
            />
          </el-form-item>

          <el-form-item label="显示名称" prop="display_name">
            <el-input v-model="userForm.display_name" maxlength="60" autocomplete="off" />
          </el-form-item>

          <el-form-item v-if="isCreateMode" label="初始密码" prop="password">
            <el-input
              v-model="userForm.password"
              type="password"
              maxlength="120"
              show-password
              autocomplete="new-password"
            />
          </el-form-item>

          <el-form-item label="启用状态">
            <el-switch
              v-model="userForm.is_active"
              active-text="启用"
              inactive-text="停用"
              :disabled="isCreateMode"
            />
          </el-form-item>
        </div>

        <el-form-item label="角色" prop="role_codes">
          <el-checkbox-group v-model="userForm.role_codes" class="role-checkboxes">
            <el-checkbox
              v-for="role in roles"
              :key="role.code"
              :value="role.code"
              class="role-checkbox"
            >
              <span>{{ role.name }}</span>
              <small>{{ role.code }}</small>
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="userDialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="resetPasswordDialogOpen"
      title="重置密码"
      width="min(520px, 96vw)"
      destroy-on-close
      @closed="clearResetPasswordDialogState"
    >
      <el-form
        ref="resetPasswordFormRef"
        :model="resetPasswordForm"
        :rules="resetPasswordRules"
        label-position="top"
        class="dialog-form"
        @submit.prevent
      >
        <p class="dialog-context">
          {{ resettingUser ? `${resettingUser.display_name}（${resettingUser.username}）` : '' }}
        </p>
        <el-form-item label="新密码" prop="password">
          <el-input
            v-model="resetPasswordForm.password"
            type="password"
            maxlength="120"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input
            v-model="resetPasswordForm.confirmPassword"
            type="password"
            maxlength="120"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="resetPasswordDialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveResetPassword">重置密码</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.admin-users-page {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.toolbar-panel,
.pagination-row,
.roles-panel,
.table-panel {
  min-width: 0;
  background: #fff;
  border: 1px solid #e2e8df;
  border-radius: 8px;
}

.toolbar-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
}

.search-input {
  width: min(360px, 100%);
}

.filter-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  min-width: 0;
}

.filter-select {
  width: 140px;
}

.table-panel {
  overflow: hidden;
}

.pagination-row {
  display: flex;
  justify-content: flex-end;
  padding: 12px;
  overflow-x: auto;
}

.roles-panel {
  display: grid;
  gap: 10px;
  padding: 14px;
}

.panel-heading {
  display: grid;
  gap: 4px;
}

.panel-heading h2 {
  margin: 0;
  color: #25342d;
  font-size: 16px;
}

.panel-heading p {
  margin: 0;
  color: #6c756f;
  font-size: 13px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}

.role-tag {
  max-width: 100%;
}

.muted-text {
  color: #8a948e;
}

.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
}

.dialog-form {
  display: grid;
  gap: 4px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 12px;
}

.role-checkboxes {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  width: 100%;
}

.role-checkbox {
  align-items: center;
  height: auto;
  min-height: 36px;
  margin-right: 0;
  padding: 7px 10px;
  border: 1px solid #e2e8df;
  border-radius: 8px;
}

.role-checkbox :deep(.el-checkbox__label) {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
  white-space: normal;
}

.role-checkbox small {
  color: #7b857f;
  font-size: 12px;
}

.dialog-context {
  margin: 0 0 12px;
  color: #536159;
  font-size: 14px;
  word-break: break-word;
}

@media (max-width: 960px) {
  .toolbar-panel,
  .filter-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .search-input,
  .filter-select {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .page-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .form-grid,
  .role-checkboxes {
    grid-template-columns: 1fr;
  }
}
</style>
