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
const itemCardGrid = readSource('src/components/items/ItemCardGrid.vue')
const itemFilterPanel = readSource('src/components/items/ItemFilterPanel.vue')
const visibleImportanceSources = [itemFormDrawer, itemDetailModal, itemTable, itemCardGrid, itemFilterPanel].join('\n')

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
assert.match(
  itemFormDrawer,
  /function buildCreatePayload[\s\S]*importance:\s*form\.importance/,
  'Item create payload should submit form importance'
)
assert.match(
  itemFormDrawer,
  /function buildUpdatePayload[\s\S]*importance:\s*form\.importance/,
  'Item update payload should submit form importance'
)
assert.match(
  itemFormDrawer,
  /dictionaryOptions\(data\.value,\s*'importance',\s*true\)/,
  'Item form should read inactive importance dictionary options for historical values'
)
assert.match(
  itemFormDrawer,
  /currentImportanceOption/,
  'Item form should compute the current historical importance option'
)
assert.match(
  itemFormDrawer,
  /allImportanceOptions\.value\.find\(\(option\) => option\.value === value\)/,
  'Item form should look up inactive importance labels for the current value'
)
assert.match(
  itemFormDrawer,
  /if \(dictionaryOption\) return \{ \.\.\.dictionaryOption, disabled: true \}/,
  'Item form should show inactive dictionary values as disabled options'
)
assert.match(
  itemFormDrawer,
  /label:\s*value[\s\S]*disabled:\s*true/,
  'Item form should show unknown historical importance values as disabled raw values'
)
assert.match(
  itemFormDrawer,
  /importanceSelectOptions/,
  'Item form should merge the current historical importance into select options'
)
assert.match(
  itemFormDrawer,
  /:disabled="option\.disabled"/,
  'Item form should prevent selecting inactive historical importance values'
)
assert.match(
  itemFormDrawer,
  /function defaultImportanceValue\(\)/,
  'Item form should centralize active importance defaults'
)
assert.match(
  itemFormDrawer,
  /option\.value === 'medium'[\s\S]*importanceOptions\.value\[0\]\?\.value[\s\S]*\?\? ''/,
  'Item form should default create importance to active medium, then first active option, then empty'
)
assert.match(
  itemFormDrawer,
  /importance:\s*defaultImportanceValue\(\)/,
  'Item create reset should use active importance defaults only'
)
assert.match(
  itemFormDrawer,
  /function validateImportance\(\): boolean/,
  'Item form should validate importance before save'
)
assert.match(
  itemFormDrawer,
  /if \(!form\.importance\)/,
  'Item form should block save when importance is empty'
)
assert.match(
  itemFormDrawer,
  /ElMessage\.error\('请选择重要程度'\)/,
  'Item form should show a clear missing importance error'
)
assert.match(itemFormDrawer, /label="重要程度"/, 'Item form should label importance in Chinese')
assert.doesNotMatch(
  visibleImportanceSources,
  /(?:label="Importance"|<span>Importance<\/span>)/,
  'Visible item importance labels should not be English'
)
assert.match(itemDetailModal, /importanceLabel/, 'Item detail should render an importance label')
assert.match(itemTable, /row\.importance/, 'Item table should render item importance')
assert.match(itemCardGrid, /dictionaryLabel/, 'Item card grid should render dictionary-backed importance labels')
assert.match(itemCardGrid, /item\.importance/, 'Item card grid should render item importance')
assert.match(itemFilterPanel, /importanceValue/, 'Item filter panel should expose importance filtering')
assert.match(itemFilterPanel, /importanceOptions/, 'Item filter panel should use dictionary options for importance')
