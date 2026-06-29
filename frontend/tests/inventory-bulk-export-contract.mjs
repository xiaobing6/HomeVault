import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const testDir = dirname(fileURLToPath(import.meta.url))
const root = resolve(testDir, '..')

function source(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const api = source('src/api/inventory.ts')
assert.match(api, /export interface BulkItemOperationResponse/)
assert.match(api, /bulkMoveItemsApi/)
assert.match(api, /bulkChangeItemStatusApi/)
assert.match(api, /bulkArchiveItemsApi/)
assert.match(api, /exportItemsCsvApi/)
assert.match(api, /responseType:\s*'blob'/)

const store = source('src/stores/inventory.ts')
assert.match(store, /bulkMoveItems/)
assert.match(store, /bulkChangeStatus/)
assert.match(store, /bulkArchiveItems/)
assert.match(store, /exportItemsCsv/)

const table = source('src/components/items/ItemTable.vue')
assert.match(table, /type="selection"/)
assert.match(table, /selection-change/)
assert.match(table, /selectedItemIds/)

const toolbar = source('src/components/items/ItemToolbar.vue')
assert.match(toolbar, /selectedCount/)
assert.match(toolbar, /bulk-move/)
assert.match(toolbar, /bulk-status/)
assert.match(toolbar, /bulk-archive/)
assert.match(toolbar, /export-selected/)
assert.match(toolbar, /export-filtered/)

const page = source('src/pages/ItemsPage.vue')
assert.match(page, /selectedItems/)
assert.match(page, /selectedItemIds/)
assert.match(page, /BulkActionDialogs/)
assert.match(page, /downloadCsvBlob/)
