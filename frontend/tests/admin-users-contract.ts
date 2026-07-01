import {
  createAdminRoleApi,
  createAdminUserApi,
  fetchAdminRolesApi,
  listAdminUsersApi,
  resetAdminUserPasswordApi,
  updateAdminRoleApi,
  updateAdminUserApi,
  type AdminPasswordResetRequest,
  type AdminRole,
  type AdminRoleCreateRequest,
  type AdminRoleUpdateRequest,
  type AdminUser,
  type AdminUserCreateRequest,
  type AdminUserFilters,
  type AdminUserListResponse,
  type AdminUserUpdateRequest
} from '../src/api/admin'
import {
  updateResidenceApi,
  type Residence,
  type ResidenceUpdate
} from '../src/api/configuration'
import AdminUsersPage from '../src/pages/AdminUsersPage.vue'
import { router } from '../src/router'
import { useAdminUsersStore } from '../src/stores/adminUsers'
import { useConfigurationStore } from '../src/stores/configuration'

function expectType<T>(_value: T): void {}

const filters: AdminUserFilters = {
  search: 'alice',
  role: 'admin',
  is_active: true,
  page: 1,
  page_size: 20
}

const createPayload: AdminUserCreateRequest = {
  username: 'alice',
  display_name: 'Alice',
  password: 'change-me',
  role_codes: ['admin']
}

const updatePayload: AdminUserUpdateRequest = {
  display_name: 'Alice Zhang',
  is_active: false,
  role_codes: ['viewer']
}

const resetPayload: AdminPasswordResetRequest = {
  password: 'new-password'
}

const roleResponse: AdminRole = {
  id: 1,
  code: 'viewer',
  name: 'Viewer',
  description: 'Read only',
  is_system: true,
  is_active: true,
  permissions: []
}
expectType<boolean>(roleResponse.is_active)

const roleCreatePayload: AdminRoleCreateRequest = {
  code: 'caretaker',
  name: 'Caretaker',
  description: 'Maintains inventory',
  permission_codes: ['items:view'],
  is_active: true
}

const roleUpdatePayload: AdminRoleUpdateRequest = {
  name: 'Caretaker Plus',
  description: 'Maintains inventory and loans',
  permission_codes: ['items:view', 'items:edit'],
  is_active: false
}

const residenceUpdatePayload: ResidenceUpdate = {
  name: 'Main Home',
  description: 'Primary residence',
  address: '123 Garden Road',
  sort_order: 10,
  is_active: false
}

async function assertAdminUsersApiContract() {
  expectType<AdminUserListResponse>(await listAdminUsersApi(filters))
  expectType<AdminRole[]>(await fetchAdminRolesApi())
  expectType<AdminUser>(await createAdminUserApi(createPayload))
  expectType<AdminUser>(await updateAdminUserApi(1, updatePayload))
  expectType<AdminUser>(await resetAdminUserPasswordApi(1, resetPayload))
  expectType<AdminRole>(await createAdminRoleApi(roleCreatePayload))
  expectType<AdminRole>(await updateAdminRoleApi(1, roleUpdatePayload))
}

async function assertResidenceConfigurationContract() {
  const configuration = useConfigurationStore()

  expectType<Residence>(await updateResidenceApi(1, residenceUpdatePayload))
  await configuration.updateResidence(1, residenceUpdatePayload)
}

async function assertAdminUsersStoreContract() {
  const adminUsers = useAdminUsersStore()

  expectType<AdminUser[]>(adminUsers.users)
  expectType<AdminRole[]>(adminUsers.roles)
  expectType<AdminUserFilters>(adminUsers.filters)
  expectType<number>(adminUsers.total)
  expectType<number>(adminUsers.page)
  expectType<number>(adminUsers.pageSize)
  expectType<boolean>(adminUsers.loading)
  expectType<boolean>(adminUsers.saving)

  await adminUsers.loadUsers({ search: 'alice' })
  await adminUsers.loadRoles()
  adminUsers.applyFilters({ role: 'admin', is_active: true })
  adminUsers.setPage(2)
  adminUsers.setPageSize(50)
  adminUsers.resetFilters()

  expectType<AdminUser>(await adminUsers.createUser(createPayload))
  expectType<AdminUser>(await adminUsers.updateUser(1, updatePayload))
  expectType<AdminUser>(await adminUsers.resetPassword(1, resetPayload))
  expectType<AdminUser>(await adminUsers.saveAndRefresh(() => updateAdminUserApi(1, updatePayload)))
  expectType<AdminRole>(await adminUsers.createRole(roleCreatePayload))
  expectType<AdminRole>(await adminUsers.updateRole(1, roleUpdatePayload))
  expectType<AdminRole>(await adminUsers.saveRoleAndRefresh(() => updateAdminRoleApi(1, roleUpdatePayload)))
}

void assertAdminUsersApiContract
void assertResidenceConfigurationContract
void assertAdminUsersStoreContract

function assertAdminUsersRouteContract() {
  expectType<object>(AdminUsersPage)

  const adminUsersRoute = router.resolve('/admin/users')
  expectType<string | symbol | null | undefined>(adminUsersRoute.name)
  expectType<unknown>(adminUsersRoute.meta.permission)

  if (adminUsersRoute.meta.permission !== 'users:manage') {
    throw new Error('Admin users route must require users:manage')
  }
}

void assertAdminUsersRouteContract
