import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const testDir = dirname(fileURLToPath(import.meta.url))
const root = resolve(testDir, '..')

function readSource(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const routerSource = readSource('src/router/index.ts')
const appLayout = readSource('src/layouts/AppLayout.vue')
const adminUsersPage = readSource('src/pages/AdminUsersPage.vue')

assert.match(routerSource, /path:\s*'admin\/users'/, 'Router should define the admin users child path')
assert.match(routerSource, /name:\s*'admin-users'/, 'Admin users route should use the admin-users name')
assert.match(routerSource, /permission:\s*'users:manage'/, 'Admin users route should require users:manage')
assert.match(appLayout, /<PermissionGate\s+permission="users:manage">/, 'Layout should gate admin users nav link')
assert.match(appLayout, /<el-menu-item\s+index="\/admin\/users">/, 'Layout should link to /admin/users')

assert.match(adminUsersPage, /useAdminUsersStore\(\)/, 'Admin users page should use the Task 3 admin users store')
assert.match(
  adminUsersPage,
  /Promise\.all\(\s*\[\s*adminUsers\.loadRoles\(\),\s*adminUsers\.loadUsers\(\)\s*\]\s*\)/s,
  'Admin users page should load roles and users concurrently on mount'
)
assert.match(
  adminUsersPage,
  /ElMessage\.error\(getChineseErrorMessage\(error\)\)/,
  'Admin users page should surface store/API errors through Chinese error messages'
)
assert.match(
  adminUsersPage,
  /import\s+\{\s*Edit,\s*Key,\s*Plus,\s*Refresh,\s*Search\s*\}\s+from\s+'@element-plus\/icons-vue'/,
  'Admin users page should use the required Element Plus icons'
)

assert.match(adminUsersPage, /<div class="page-heading">/, 'Admin users page should use the shared page heading pattern')
assert.match(adminUsersPage, /<div class="toolbar-panel">/, 'Admin users page should include a toolbar panel')
assert.match(adminUsersPage, /<div class="table-panel">/, 'Admin users page should include a table panel')
assert.match(adminUsersPage, /<div class="pagination-row">/, 'Admin users page should include a pagination row')
assert.match(adminUsersPage, /<div class="roles-panel">/, 'Admin users page should include a roles reference panel')

assert.match(adminUsersPage, /v-model="searchValue"/, 'Toolbar search input should be bound to store search')
assert.match(adminUsersPage, /@keyup\.enter="loadUsers"/, 'Search input should load on Enter')
assert.match(adminUsersPage, /@clear="loadUsers"/, 'Search clear should reload users')
assert.match(adminUsersPage, /v-model="roleValue"/, 'Toolbar role filter should be bound to store role filter')
assert.match(adminUsersPage, /v-model="activeValue"/, 'Toolbar active filter should be bound to store active filter')
assert.match(adminUsersPage, /@click="resetFilters"/, 'Toolbar should provide a reset filters action')

assert.match(
  adminUsersPage,
  /<el-table\s+v-loading="loading"\s+:data="users"\s+row-key="id"\s+empty-text="暂无用户"/s,
  'Users table should use store users, loading state, row key, and empty text'
)
for (const label of ['用户名', '显示名称', '角色', '状态', '更新时间', '操作']) {
  assert.match(adminUsersPage, new RegExp(`label="${label}"`), `Users table should include ${label} column`)
}
assert.match(adminUsersPage, /openEditDialog\(row\)/, 'Users table should provide an edit action')
assert.match(adminUsersPage, /openResetPasswordDialog\(row\)/, 'Users table should provide a reset password action')

assert.match(
  adminUsersPage,
  /<el-pagination[\s\S]*:page-sizes="\[20,\s*40,\s*80\]"[\s\S]*@current-change="changePage"[\s\S]*@size-change="changePageSize"/,
  'Pagination should be bound to the admin users store page controls'
)

assert.match(adminUsersPage, /role\.permissions/, 'Roles panel should list permissions from each role')
assert.match(adminUsersPage, /permission\.code/, 'Roles panel should display permission codes')

assert.match(adminUsersPage, /const defaultUserForm/, 'Create dialog should define default form state')
assert.match(adminUsersPage, /role_codes:\s*defaultRoleCodes\(\)/, 'Default create role should come from viewer fallback logic')
assert.match(adminUsersPage, /const payload: AdminUserCreateRequest/, 'Create save should use the create payload type')
const createPayloadStart = adminUsersPage.indexOf('const payload: AdminUserCreateRequest')
const createPayloadEnd = adminUsersPage.indexOf('await adminUsers.createUser(payload)', createPayloadStart)
assert.notEqual(createPayloadStart, -1, 'Create payload block should exist')
assert.notEqual(createPayloadEnd, -1, 'Create save call should exist')
assert.doesNotMatch(
  adminUsersPage.slice(createPayloadStart, createPayloadEnd),
  /is_active/,
  'Create payload must not send is_active because backend creates active users'
)
assert.match(adminUsersPage, /await adminUsers\.updateUser\(/, 'Edit save should call adminUsers.updateUser')
assert.match(adminUsersPage, /await adminUsers\.resetPassword\(/, 'Reset dialog should call adminUsers.resetPassword')
assert.match(adminUsersPage, /confirmPassword/, 'Reset password dialog should validate confirmation')
assert.match(
  adminUsersPage,
  /toLocaleString\('zh-CN',\s*\{\s*hour12:\s*false\s*\}\)/,
  'Updated date formatting should use zh-CN 24-hour locale'
)
assert.match(adminUsersPage, /Number\.isNaN\(date\.getTime\(\)\)/, 'Invalid date formatting should fall back to the raw value')
