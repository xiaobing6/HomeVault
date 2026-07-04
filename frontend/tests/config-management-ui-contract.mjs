import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const testDir = dirname(fileURLToPath(import.meta.url))
const root = resolve(testDir, '..')

function readSource(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

function interfaceSource(source, name) {
  const match = source.match(new RegExp(`export interface ${name} \\{([\\s\\S]*?)\\n\\}`))
  assert.ok(match, `Expected ${name} interface to exist`)
  return match[1]
}

const residenceLocationPanel = readSource('src/components/config/ResidenceLocationPanel.vue')
const configurationApi = readSource('src/api/configuration.ts')
const familyMemberPanel = readSource('src/components/config/FamilyMemberPanel.vue')
const categoryFieldPanel = readSource('src/components/config/CategoryFieldPanel.vue')
const dictionaryPanel = readSource('src/components/config/DictionaryPanel.vue')
const customFieldInputs = readSource('src/components/items/CustomFieldInputs.vue')
const appLayout = readSource('src/layouts/AppLayout.vue')
const coreConfigPage = readSource('src/pages/CoreConfigPage.vue')

assert.match(appLayout, /<el-sub-menu\s+index="admin-config"/, 'Layout should render backend management as a collapsible submenu')
for (const label of ['住宅与位置', '家庭成员', '分类字段', '状态与字典']) {
  assert.match(appLayout, new RegExp(label), `Backend management submenu should include ${label}`)
}
assert.match(appLayout, /class="account-footer"/, 'Account information should live in the sidebar footer')
assert.doesNotMatch(appLayout, /class="top-bar"/, 'Account information should not remain in a top header bar')

assert.match(coreConfigPage, /const\s+activeSection\s*=\s*computed/, 'Core config page should derive the active admin section from the sidebar route')
assert.doesNotMatch(
  coreConfigPage,
  /<el-tabs[\s\S]*class="config-tabs"/,
  'Core config page should not render a second backend-management tab bar in the content area'
)
for (const section of ['residence-location', 'family-members', 'category-fields', 'status-dictionaries']) {
  assert.match(coreConfigPage, new RegExp(`activeSection === '${section}'`), `Core config page should render ${section} from sidebar routing`)
}

assert.match(
  residenceLocationPanel,
  /const\s+activeResourceTab\s*=\s*ref\('residences'\)/,
  'Residence/location panel should keep separate residence and location tabs'
)
assert.match(
  residenceLocationPanel,
  /const\s+residenceCreateOpen\s*=\s*ref\(false\)/,
  'Residence creation should open from a dialog instead of an inline form'
)
assert.match(
  residenceLocationPanel,
  /const\s+locationCreateOpen\s*=\s*ref\(false\)/,
  'Location creation should open from a dialog instead of an inline form'
)
assert.match(
  residenceLocationPanel,
  /const\s+selectedResidence\s*=\s*ref<Residence\s*\|\s*null>\(null\)/,
  'Residence cards should open a detail view'
)
assert.match(
  residenceLocationPanel,
  /const\s+selectedLocation\s*=\s*ref<LocationNode\s*\|\s*null>\(null\)/,
  'Location cards should open a detail view'
)
assert.match(
  residenceLocationPanel,
  /const\s+locationResidenceFilter\s*=\s*ref<number\s*\|\s*''\s*\|\s*null\s*\|\s*undefined>\(''\)/,
  'Location list should include a residence filter'
)
assert.match(
  residenceLocationPanel,
  /const\s+locationTypeFilter\s*=\s*ref<string\s*\|\s*null\s*\|\s*undefined>\(''\)/,
  'Location list should include a type filter'
)
assert.match(
  residenceLocationPanel,
  /function\s+hasResidenceFilter\([^)]*value:[^)]*\)[\s\S]*typeof\s+value\s*===\s*'number'/,
  'Clearing the residence filter should normalize to all residences'
)
assert.match(
  residenceLocationPanel,
  /function\s+hasLocationTypeFilter\([^)]*value:[^)]*\)[\s\S]*value\.length\s*>\s*0/,
  'Clearing the location type filter should normalize to all location types'
)
assert.match(
  residenceLocationPanel,
  /!hasResidenceFilter\(selectedResidenceId\)[\s\S]*card\.node\.residence_id\s*===\s*selectedResidenceId/,
  'Location residence filtering should treat cleared values as all residences'
)
assert.match(
  residenceLocationPanel,
  /!hasLocationTypeFilter\(selectedLocationType\)[\s\S]*card\.node\.node_type\s*===\s*selectedLocationType/,
  'Location type filtering should treat cleared values as all types'
)
assert.match(residenceLocationPanel, /class="residence-card-grid"/, 'Residence list should render a card grid')
assert.match(residenceLocationPanel, /class="location-card-grid"/, 'Location list should render a card grid')
assert.match(residenceLocationPanel, /class="section-heading"/, 'Residence/location panel should own the visible page title')
assert.match(residenceLocationPanel, /class="resource-tabs-shell"/, 'Residence/location panel should keep actions aligned with the residence/location tabs')
assert.match(residenceLocationPanel, /class="resource-tab-actions"/, 'New actions and location filters should sit on the tab row')
assert.doesNotMatch(
  residenceLocationPanel,
  /\.residence-location-panel\s*\{[^}]*max-width/,
  'Residence/location panel should not leave unused width on wide screens'
)
assert.doesNotMatch(
  residenceLocationPanel,
  /padding-right:\s*420px/,
  'Residence/location tabs should not reserve a fixed empty area for the action button'
)
assert.match(
  residenceLocationPanel,
  /\.resource-tabs-shell[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)\s+auto/,
  'Residence/location tab row should let tabs fill available width and place actions at the right edge'
)
assert.match(
  residenceLocationPanel,
  /residence-card-grid[\s\S]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/,
  'Residence cards should show at most two per row'
)
assert.match(
  residenceLocationPanel,
  /residence-card-grid[\s\S]*gap:\s*16px/,
  'Residence card rows and columns should keep consistent spacing'
)
assert.match(
  residenceLocationPanel,
  /\.resource-card[\s\S]*width:\s*100%/,
  'Resource cards should stretch to fill their grid column'
)
assert.match(
  residenceLocationPanel,
  /location-card-grid[\s\S]*grid-template-columns:\s*repeat\(4,\s*minmax\(0,\s*1fr\)\)/,
  'Location cards should show at most four per row'
)
assert.match(
  residenceLocationPanel,
  /location-card-grid[\s\S]*gap:\s*16px/,
  'Location card rows and columns should keep consistent spacing'
)
assert.match(
  residenceLocationPanel,
  /class="card-cover location-cover"/,
  'Location cards should use the same image-cover card structure as residences'
)
assert.doesNotMatch(
  residenceLocationPanel,
  /class="location-card-head"/,
  'Location cards should not use the old compact icon-card header'
)
assert.match(residenceLocationPanel, /class="resource-detail"/, 'Residence/location detail view should use a dedicated detail layout')
assert.doesNotMatch(
  residenceLocationPanel,
  /CirclePlus/,
  'Residence and location new buttons should use the same plus icon style'
)
assert.match(
  residenceLocationPanel,
  /<el-button[\s\S]*v-if="activeResourceTab === 'residences'"[\s\S]*type="primary"[\s\S]*:icon="Plus"[\s\S]*round[\s\S]*新建住宅/,
  'New residence button should use the shared primary rounded plus-button style'
)
assert.match(
  residenceLocationPanel,
  /<el-button[\s\S]*type="primary"[\s\S]*:icon="Plus"[\s\S]*round[\s\S]*@click="openLocationCreate"[\s\S]*新建位置/,
  'New location button should use the shared primary rounded plus-button style'
)
assert.match(
  residenceLocationPanel,
  /v-if="isShowingDetail"\s+class="resource-detail-shell"/,
  'Residence/location details should render in their own shell outside list tabs'
)
assert.match(
  residenceLocationPanel,
  /v-else\s+class="resource-list-shell"/,
  'Residence/location list mode should be separated from detail mode'
)
assert.doesNotMatch(
  residenceLocationPanel,
  /<el-tabs[\s\S]*selectedResidenceDetail/,
  'Residence detail should not render inside the residence/location tabs'
)
assert.doesNotMatch(
  residenceLocationPanel,
  /<el-tabs[\s\S]*selectedLocationDetail/,
  'Location detail should not render inside the residence/location tabs'
)
assert.match(
  residenceLocationPanel,
  /\.resource-detail-shell[\s\S]*max-width:\s*1040px[\s\S]*margin:\s*0\s+auto/,
  'Detail content should be centered with a fixed readable max width'
)
assert.match(
  residenceLocationPanel,
  /\.resource-detail-shell[\s\S]*padding-inline:\s*clamp\(/,
  'Detail content should keep symmetric horizontal breathing room'
)
assert.match(residenceLocationPanel, /openResidenceCreate/, 'Residence toolbar should expose a new residence action')
assert.match(residenceLocationPanel, /openLocationCreate/, 'Location toolbar should expose a new location action')
for (const field of [
  'created_at: string',
  'updated_at: string',
  'created_by_id: number | null',
  'created_by_name: string | null',
  'updated_by_id: number | null',
  'updated_by_name: string | null',
  'image_url: string | null'
]) {
  assert.match(
    interfaceSource(configurationApi, 'Residence'),
    new RegExp(field.replace(/[|]/g, '\\|').replace(/\s+/g, '\\s*')),
    `Residence API type should expose ${field}`
  )
}
assert.doesNotMatch(
  interfaceSource(configurationApi, 'Residence'),
  /sort_order:/,
  'Residence API type should no longer expose sort_order'
)
assert.doesNotMatch(
  `${interfaceSource(configurationApi, 'ResidenceCreate')}\n${interfaceSource(configurationApi, 'ResidenceUpdate')}`,
  /sort_order:/,
  'Residence create/update payloads should no longer accept sort_order'
)
assert.match(
  configurationApi,
  /uploadResidenceImageApi\([^)]*residenceId:\s*number[\s\S]*file:\s*File/,
  'Residence API should upload or replace a local image file'
)
assert.match(
  residenceLocationPanel,
  /v-model:file-list="residenceImageFiles"/,
  'New residence dialog should allow choosing a local image file'
)
assert.match(
  residenceLocationPanel,
  /v-model:file-list="residenceEditImageFiles"/,
  'Residence edit dialog should allow replacing the image file'
)
assert.doesNotMatch(
  residenceLocationPanel,
  /residenceEditForm\.sort_order|selectedResidenceDetail\.sort_order/,
  'Residence edit and detail UI should not expose sort order'
)
assert.doesNotMatch(
  residenceLocationPanel,
  /placeholder="[^"]*（选填）[^"]*"/,
  'Residence description placeholder should not include optional copy'
)
assert.match(
  residenceLocationPanel,
  /formatDateTime\(selectedResidenceDetail\.created_at\)[\s\S]*selectedResidenceDetail\.created_by_name[\s\S]*formatDateTime\(selectedResidenceDetail\.updated_at\)[\s\S]*selectedResidenceDetail\.updated_by_name/,
  'Residence detail should show created/updated timestamps and users'
)
assert.match(
  residenceLocationPanel,
  /ProtectedImage[\s\S]*residence\.image_url|ProtectedImage[\s\S]*selectedResidenceDetail\.image_url/,
  'Residence cards or detail should render protected uploaded images when present'
)

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
assert.match(
  dictionaryPanel,
  /configuration\.updateDictionaryOption\(\s*editingDictionaryOption\.value\.id/,
  'Dictionary panel should update existing dictionary options'
)
assert.match(
  dictionaryPanel,
  /<el-switch[\s\S]*v-model="dictionaryOptionEditForm\.is_active"/,
  'Dictionary option edit dialog should expose active state'
)
assert.doesNotMatch(
  dictionaryPanel,
  /configuration\.createDictionaryOption|configuration\.createDictionaryGroup|deleteDictionaryOption|deleteDictionaryGroup/,
  'Dictionary panel should not expose dictionary create or delete controls'
)
assert.match(
  residenceLocationPanel,
  /locationNodeTypeOptions/,
  'Location panel should compute location type options from dictionaries'
)
assert.match(
  residenceLocationPanel,
  /locationNodeTypeEditOptions/,
  'Location edit type options should merge active options with the current saved value'
)
assert.match(
  residenceLocationPanel,
  /if\s*\(!locationForm\.node_type\)\s*\{[\s\S]*ElMessage\.error/,
  'Location create save should block clearly when no active location type is selectable'
)
assert.doesNotMatch(
  residenceLocationPanel,
  /const\s+locationTypes\s*=\s*\[/,
  'Location type options should not be hard-coded in the location panel'
)
assert.doesNotMatch(
  residenceLocationPanel,
  /node_type:\s*'room'|node_type:\s*locationNodeTypeOptions\.value\[0\]\?\.value\s*\?\?\s*'room'/,
  'Location create/edit state should not blindly fall back to the room type'
)
