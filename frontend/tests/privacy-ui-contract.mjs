import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const readSource = (path) => readFileSync(resolve(root, path), 'utf8')

const itemFormDrawer = readSource('src/components/items/ItemFormDrawer.vue')
const itemDetailModal = readSource('src/components/items/ItemDetailModal.vue')
const inventoryApi = readSource('src/api/inventory.ts')
const configurationApi = readSource('src/api/configuration.ts')

assert.match(itemFormDrawer, /value:\s*'sensitive'/)
assert.doesNotMatch(itemFormDrawer, /value:\s*'(private|encrypted)'/)
assert.doesNotMatch(itemFormDrawer, /privacy_level:\s*string/)
assert.match(itemFormDrawer, /privacy_level:\s*PrivacyLevel/)
assert.match(itemDetailModal, /level === 'sensitive'/)
assert.doesNotMatch(itemDetailModal, /level === '(private|encrypted)'/)

for (const source of [inventoryApi, configurationApi]) {
  assert.match(source, /export type PrivacyLevel = 'normal' \| 'sensitive'/)
  assert.match(source, /privacy_level\??: PrivacyLevel/)
}
