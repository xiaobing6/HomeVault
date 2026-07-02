import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const testDir = dirname(fileURLToPath(import.meta.url))
const root = resolve(testDir, '..')

function readSource(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

function readInterfaceBlock(source, interfaceName) {
  const interfacePattern = new RegExp(
    `export interface ${interfaceName}\\s*\\{[\\s\\S]*?\\r?\\n\\}`
  )
  const match = source.match(interfacePattern)
  assert.ok(match, `${interfaceName} interface should exist`)
  return match[0]
}

const inventoryApi = readSource('src/api/inventory.ts')
const itemFormDrawer = readSource('src/components/items/ItemFormDrawer.vue')
const itemDetailModal = readSource('src/components/items/ItemDetailModal.vue')
const itemTable = readSource('src/components/items/ItemTable.vue')
const itemFilterPanel = readSource('src/components/items/ItemFilterPanel.vue')

const itemSummary = readInterfaceBlock(inventoryApi, 'ItemSummary')
const itemFilters = readInterfaceBlock(inventoryApi, 'ItemFilters')
const itemCreateRequest = readInterfaceBlock(inventoryApi, 'ItemCreateRequest')
const itemUpdateRequest = readInterfaceBlock(inventoryApi, 'ItemUpdateRequest')

assert.match(itemSummary, /importance:\s*string/, 'Inventory item summary should expose importance')
assert.match(itemFilters, /importance\?:\s*string\s*\|\s*null/, 'Inventory filters should accept importance')
assert.match(itemCreateRequest, /importance\?:\s*string/, 'Inventory create payload should accept importance')
assert.match(itemUpdateRequest, /importance\?:\s*string/, 'Inventory update payload should accept importance')
assert.match(itemFormDrawer, /importanceOptions/, 'Item form should compute importance dictionary options')
assert.match(itemFormDrawer, /v-model="form\.importance"/, 'Item form should bind importance select')
assert.match(itemDetailModal, /importanceLabel/, 'Item detail should render an importance label')
assert.match(itemTable, /row\.importance/, 'Item table should render item importance')
assert.match(itemFilterPanel, /importanceValue/, 'Item filter panel should expose importance filtering')
assert.match(itemFilterPanel, /importanceOptions/, 'Item filter panel should use dictionary options for importance')
