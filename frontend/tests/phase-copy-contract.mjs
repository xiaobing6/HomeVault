import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const testDir = dirname(fileURLToPath(import.meta.url))
const root = resolve(testDir, '..')
const staleCopy = /第一阶段|后续展示|后续管理功能|准备接入|后续阶段会继续补齐.*(?:审计|管理)|管理员、编辑者、查看者已预留/

for (const relativePath of ['src/pages/DashboardPage.vue', 'src/pages/LoginPage.vue']) {
  const source = readFileSync(resolve(root, relativePath), 'utf8')
  assert.doesNotMatch(source, staleCopy, `${relativePath} should not show stale phase placeholder copy`)
}
