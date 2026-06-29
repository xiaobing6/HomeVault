import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const testDir = dirname(fileURLToPath(import.meta.url))
const root = resolve(testDir, '..')

function readSource(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const residenceLocationPanel = readSource('src/components/config/ResidenceLocationPanel.vue')
const familyMemberPanel = readSource('src/components/config/FamilyMemberPanel.vue')
const categoryFieldPanel = readSource('src/components/config/CategoryFieldPanel.vue')
const dictionaryPanel = readSource('src/components/config/DictionaryPanel.vue')
const customFieldInputs = readSource('src/components/items/CustomFieldInputs.vue')

assert.match(
  residenceLocationPanel,
  /const\s+locationEditOpen\s*=\s*ref\(/,
  'Location panel should track location edit dialog state'
)
assert.match(
  residenceLocationPanel,
  /function\s+openLocationEdit\(\s*location:\s*LocationNode\s*\)/,
  'Location panel should open a location edit dialog from a tree node'
)
assert.match(
  residenceLocationPanel,
  /configuration\.updateLocationNode\(\s*editingLocation\.value\.id/,
  'Location edit save should call configuration.updateLocationNode'
)
assert.match(
  residenceLocationPanel,
  /<el-switch[\s\S]*v-model="locationEditForm\.is_active"/,
  'Location edit dialog should expose active state with a switch'
)

assert.match(
  familyMemberPanel,
  /const\s+memberEditOpen\s*=\s*ref\(/,
  'Family member panel should track member edit dialog state'
)
assert.match(
  familyMemberPanel,
  /function\s+openMemberEdit\(\s*member:\s*FamilyMember\s*\)/,
  'Family member panel should open an edit dialog'
)
assert.match(
  familyMemberPanel,
  /configuration\.updateFamilyMember\(\s*editingMember\.value\.id/,
  'Family member edit save should call configuration.updateFamilyMember'
)
assert.match(
  familyMemberPanel,
  /<el-switch[\s\S]*v-model="memberEditForm\.is_active"/,
  'Family member edit dialog should expose active state with a switch'
)

assert.match(
  categoryFieldPanel,
  /function\s+openCategoryEdit\(\s*category:\s*Category\s*\)/,
  'Category panel should open a category edit dialog'
)
assert.match(
  categoryFieldPanel,
  /configuration\.updateCategory\(\s*editingCategory\.value\.id/,
  'Category edit save should call configuration.updateCategory'
)
assert.match(
  categoryFieldPanel,
  /function\s+openFieldEdit\(\s*field:\s*AttributeDefinition\s*\)/,
  'Field panel should open an attribute definition edit dialog'
)
assert.match(
  categoryFieldPanel,
  /configuration\.updateAttributeDefinition\(\s*editingField\.value\.id/,
  'Field edit save should call configuration.updateAttributeDefinition'
)
assert.match(
  categoryFieldPanel,
  /configuration\.createAttributeOption\(/,
  'Field panel should create attribute options for select fields'
)
assert.match(
  categoryFieldPanel,
  /configuration\.updateAttributeOption\(\s*editingOption\.value\.id/,
  'Field panel should update existing attribute options'
)
assert.match(
  categoryFieldPanel,
  /<el-switch[\s\S]*v-model="categoryEditForm\.is_active"/,
  'Category edit dialog should expose active state with a switch'
)
assert.match(
  categoryFieldPanel,
  /<el-switch[\s\S]*v-model="fieldEditForm\.is_active"/,
  'Field edit dialog should expose active state with a switch'
)
assert.match(
  categoryFieldPanel,
  /<el-select[^>]*v-model="fieldEditForm\.privacy_level"/,
  'Field privacy level should be selected from fixed options'
)
assert.match(
  categoryFieldPanel,
  /<el-select[^>]*v-model="fieldForm\.privacy_level"/,
  'New field privacy level should be selected from fixed options'
)
assert.doesNotMatch(
  categoryFieldPanel,
  /<el-input[^>]*v-model="fieldEditForm\.privacy_level"/,
  'Field privacy level should not be free-form text'
)
assert.doesNotMatch(
  categoryFieldPanel,
  /<el-input[^>]*v-model="fieldForm\.privacy_level"/,
  'New field privacy level should not be free-form text'
)
assert.doesNotMatch(
  categoryFieldPanel,
  /encrypted_text/,
  'Encrypted text field type should be removed from field configuration options'
)
assert.doesNotMatch(
  customFieldInputs,
  /encrypted_text/,
  'Encrypted text field type should not have a custom input renderer'
)
assert.match(
  categoryFieldPanel,
  /<el-switch[\s\S]*v-model="optionEditForm\.is_active"/,
  'Attribute option edit dialog should expose active state with a switch'
)

assert.match(
  dictionaryPanel,
  /configuration\.createItemStatus\(/,
  'Dictionary panel should create item statuses'
)
assert.match(
  dictionaryPanel,
  /configuration\.updateItemStatus\(\s*editingStatus\.value\.id/,
  'Dictionary panel should update item statuses'
)
assert.match(
  dictionaryPanel,
  /<el-switch[\s\S]*v-model="statusEditForm\.is_active"/,
  'Item status edit dialog should expose active state with a switch'
)
assert.doesNotMatch(
  dictionaryPanel,
  /updateDictionary(Group|Option)|dictionary(Group|Option)EditOpen|openDictionary(Group|Option)Edit|dictionaryEditOpen|openDictionaryEdit/,
  'Dictionary groups and dictionary options should remain read-only in this slice'
)
