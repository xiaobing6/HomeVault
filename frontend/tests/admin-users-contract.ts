import {
  createAdminUserApi,
  fetchAdminRolesApi,
  listAdminUsersApi,
  resetAdminUserPasswordApi,
  updateAdminUserApi,
  type AdminPasswordResetRequest,
  type AdminRole,
  type AdminUser,
  type AdminUserCreateRequest,
  type AdminUserFilters,
  type AdminUserListResponse,
  type AdminUserUpdateRequest
} from '../src/api/admin'
import AdminUsersPage from '../src/pages/AdminUsersPage.vue'
import { router } from '../src/router'
import { useAdminUsersStore } from '../src/stores/adminUsers'

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

async function assertAdminUsersApiContract() {
  expectType<AdminUserListResponse>(await listAdminUsersApi(filters))
  expectType<AdminRole[]>(await fetchAdminRolesApi())
  expectType<AdminUser>(await createAdminUserApi(createPayload))
  expectType<AdminUser>(await updateAdminUserApi(1, updatePayload))
  expectType<AdminUser>(await resetAdminUserPasswordApi(1, resetPayload))
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
}

void assertAdminUsersApiContract
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
