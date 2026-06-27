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
const iconImport = adminUsersPage.match(
  /import\s+\{\s*([^}]+?)\s*\}\s+from\s+'@element-plus\/icons-vue'/s
)
assert.ok(iconImport, 'Admin users page should import Element Plus icons')
const importedIcons = new Set(iconImport[1].split(',').map((name) => name.trim()))
for (const requiredIcon of ['Edit', 'Key', 'Plus', 'Refresh', 'Search']) {
  assert.ok(
    importedIcons.has(requiredIcon),
    `Admin users page should import the ${requiredIcon} Element Plus icon`
  )
}
assert.doesNotMatch(
  adminUsersPage,
  /set:\s*\(\s*value:\s*string\s*\)\s*=>\s*\{[\s\S]*?adminUsers\.applyFilters\(\s*\{\s*search:/,
  'Typing in the search box should not commit search filters before an explicit submit'
)

assert.match(adminUsersPage, /<div class="page-heading">/, 'Admin users page should use the shared page heading pattern')
assert.match(adminUsersPage, /<div class="toolbar-panel">/, 'Admin users page should include a toolbar panel')
assert.match(adminUsersPage, /<div class="table-panel">/, 'Admin users page should include a table panel')
assert.match(adminUsersPage, /<div class="pagination-row">/, 'Admin users page should include a pagination row')
assert.match(adminUsersPage, /<div class="roles-panel">/, 'Admin users page should include a roles reference panel')

assert.match(adminUsersPage, /const\s+searchDraft\s*=\s*ref\(/, 'Toolbar search should keep local draft state')
assert.match(adminUsersPage, /v-model="searchDraft"/, 'Toolbar search input should be bound to local draft state')
assert.doesNotMatch(adminUsersPage, /v-model="searchValue"/, 'Toolbar search input should not write through to store state on input')
assert.match(adminUsersPage, /@keyup\.enter="loadUsers"/, 'Search input should load on Enter')
assert.match(adminUsersPage, /@clear="clearSearch"/, 'Search clear should clear draft and reload users')
assert.match(
  adminUsersPage,
  /function\s+submittedSearch\(\)[\s\S]*searchDraft\.value\.trim\(\)[\s\S]*return\s+search\s*\|\|\s*null/,
  'Search submit should trim the draft before loading users'
)
assert.match(
  adminUsersPage,
  /async\s+function\s+clearSearch\(\)[\s\S]*searchDraft\.value\s*=\s*''[\s\S]*loadUsers\(\)/,
  'Search clear should clear the draft before loading users'
)
assert.match(
  adminUsersPage,
  /async\s+function\s+resetFilters\(\)[\s\S]*adminUsers\.resetFilters\(\)[\s\S]*syncSearchDraftFromFilters\(\)[\s\S]*adminUsers\.loadUsers\(\)/,
  'Reset filters should synchronize the local search draft before reloading users'
)
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
assert.match(
  adminUsersPage,
  /(value\s*!==\s*resetPasswordForm\.password|resetPasswordForm\.password\s*!==\s*value)/,
  'Reset password dialog should compare confirmation against the password field'
)
assert.match(
  adminUsersPage,
  /@closed="clearUserDialogState"/,
  'Create/edit dialog should clear sensitive state after it closes'
)
assert.match(
  adminUsersPage,
  /function\s+clearUserDialogState\(\)[\s\S]*userForm\.password\s*=\s*''[\s\S]*editingUser\.value\s*=\s*null/,
  'Create/edit dialog close handler should clear password and editing user state'
)
assert.match(
  adminUsersPage,
  /@closed="clearResetPasswordDialogState"/,
  'Reset password dialog should clear sensitive state after it closes'
)
assert.match(
  adminUsersPage,
  /function\s+clearResetPasswordDialogState\(\)[\s\S]*resetPasswordForm\.password\s*=\s*''[\s\S]*resetPasswordForm\.confirmPassword\s*=\s*''[\s\S]*resettingUser\.value\s*=\s*null/,
  'Reset password dialog close handler should clear both password fields and resetting user state'
)
const saveUserStart = adminUsersPage.indexOf('async function saveUser()')
const saveUserEnd = adminUsersPage.indexOf('function openResetPasswordDialog', saveUserStart)
assert.notEqual(saveUserStart, -1, 'Save user function should exist')
assert.notEqual(saveUserEnd, -1, 'Reset password dialog opener should follow save user')
assert.match(
  adminUsersPage.slice(saveUserStart, saveUserEnd),
  /clearUserDialogState\(\)/,
  'Successful user save should immediately clear sensitive user dialog state'
)
const saveResetStart = adminUsersPage.indexOf('async function saveResetPassword()')
assert.notEqual(saveResetStart, -1, 'Save reset password function should exist')
assert.match(
  adminUsersPage.slice(saveResetStart),
  /clearResetPasswordDialogState\(\)/,
  'Successful password reset should immediately clear sensitive reset dialog state'
)
assert.match(
  adminUsersPage,
  /toLocaleString\('zh-CN',\s*\{\s*hour12:\s*false\s*\}\)/,
  'Updated date formatting should use zh-CN 24-hour locale'
)
assert.match(adminUsersPage, /Number\.isNaN\(date\.getTime\(\)\)/, 'Invalid date formatting should fall back to the raw value')
