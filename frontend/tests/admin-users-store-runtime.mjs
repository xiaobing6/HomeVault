import assert from 'node:assert/strict'

import { createServer } from 'vite'

function buildUser(id) {
  return {
    id,
    username: `user${id}`,
    display_name: `User ${id}`,
    is_active: true,
    roles: ['admin'],
    permissions: ['users:manage'],
    created_at: '2026-06-20T00:00:00Z',
    updated_at: '2026-06-20T00:00:00Z'
  }
}

function buildRole(id) {
  return {
    id,
    code: 'admin',
    name: 'Admin',
    description: 'System administrator',
    is_system: true,
    permissions: [
      {
        code: 'users:manage',
        name: 'Manage users',
        description: 'Manage admin users'
      }
    ]
  }
}

function buildUserList(page = 1) {
  return {
    items: [buildUser(page)],
    total: 1,
    page,
    page_size: 20
  }
}

function buildResponse(config, data) {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config
  }
}

function deferredResponse(config, data) {
  let resolveResponse
  const promise = new Promise((resolve) => {
    resolveResponse = () => resolve(buildResponse(config, data))
  })
  return { promise, resolveResponse }
}

const server = await createServer({
  root: process.cwd(),
  logLevel: 'error',
  server: { middlewareMode: true },
  appType: 'custom'
})

try {
  const { createPinia } = await server.ssrLoadModule('pinia')
  const { apiClient } = await server.ssrLoadModule('/src/api/client.ts')
  const { useAdminUsersStore } = await server.ssrLoadModule('/src/stores/adminUsers.ts')

  const pinia = createPinia()
  const adminUsers = useAdminUsersStore(pinia)

  let usersResponse
  let rolesResponse

  apiClient.defaults.adapter = async (config) => {
    if (config.url === '/admin/users') {
      usersResponse = deferredResponse(config, buildUserList(1))
      return await usersResponse.promise
    }
    if (config.url === '/admin/roles') {
      rolesResponse = deferredResponse(config, [buildRole(1)])
      return await rolesResponse.promise
    }
    throw new Error(`Unexpected request: ${config.url}`)
  }

  const usersLoad = adminUsers.loadUsers()
  const rolesLoad = adminUsers.loadRoles()

  assert.equal(adminUsers.loading, true, 'loading should be true while admin store requests are active')

  rolesResponse.resolveResponse()
  await rolesLoad

  assert.equal(
    adminUsers.loading,
    true,
    'loading should remain true after roles finish while users are still loading'
  )

  usersResponse.resolveResponse()
  await usersLoad

  assert.equal(adminUsers.loading, false, 'loading should be false after all active admin loads finish')
  assert.equal(adminUsers.users[0]?.id, 1)
  assert.equal(adminUsers.roles[0]?.id, 1)

  let requestedUserParams
  apiClient.defaults.adapter = async (config) => {
    if (config.url === '/admin/users') {
      requestedUserParams = config.params
      return buildResponse(config, buildUserList(1))
    }
    throw new Error(`Unexpected request: ${config.url}`)
  }

  adminUsers.setPage(3)
  await adminUsers.loadUsers({ search: 'alice' })

  assert.equal(requestedUserParams.page, 1, 'non-pagination filters should reset loadUsers to page 1')
  assert.equal(adminUsers.page, 1, 'store page should match the reset API response page')
} finally {
  await server.close()
}
