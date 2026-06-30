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
assert.match(api, /export interface ImportPreviewResponse/)
assert.match(api, /downloadImportTemplateApi/)
assert.match(api, /previewInventoryImportApi/)
assert.match(api, /confirmInventoryImportApi/)
assert.match(api, /FormData/)
assert.match(api, /\/items\/import\/template\.csv/)
assert.match(api, /\/items\/import\/preview/)
assert.match(api, /\/items\/import\/confirm/)

const store = source('src/stores/inventory.ts')
assert.match(store, /downloadImportTemplate/)
assert.match(store, /previewInventoryImport/)
assert.match(store, /confirmInventoryImport/)

const toolbar = source('src/components/items/ItemToolbar.vue')
assert.match(toolbar, /import-items/)
assert.match(toolbar, /Upload/)

const page = source('src/pages/ItemsPage.vue')
assert.match(page, /ItemImportDialog/)
assert.match(page, /importDialogOpen/)
assert.match(page, /downloadImportTemplateBlob/)

const dialog = source('src/components/items/ItemImportDialog.vue')
assert.match(dialog, /previewInventoryImport/)
assert.match(dialog, /confirmInventoryImport/)
assert.match(dialog, /invalid_count/)
assert.match(dialog, /row_number/)
assert.match(dialog, /errors/)
