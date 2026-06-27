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

assert.match(routerSource, /path:\s*'admin\/users'/, 'Router should define the admin users child path')
assert.match(routerSource, /name:\s*'admin-users'/, 'Admin users route should use the admin-users name')
assert.match(routerSource, /permission:\s*'users:manage'/, 'Admin users route should require users:manage')
assert.match(appLayout, /<PermissionGate\s+permission="users:manage">/, 'Layout should gate admin users nav link')
assert.match(appLayout, /<el-menu-item\s+index="\/admin\/users">/, 'Layout should link to /admin/users')
