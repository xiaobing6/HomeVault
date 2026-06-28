# HomeVault Phase 4C-2 Configuration Management Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add edit, activate, and deactivate controls for core configuration records that already have backend update APIs.

**Architecture:** Keep this frontend-first. Add typed API helpers and Pinia store actions for the existing PATCH endpoints, then wire those actions into the existing Element Plus configuration panels. Each panel owns its dialog/form state because locations, members, categories, fields, options, and statuses have different payload rules.

**Tech Stack:** Vue 3, TypeScript, Pinia, Element Plus, Axios, FastAPI backend contract tests.

---

## File Structure

- Modify `frontend/src/api/configuration.ts`: add update/create payload types and API helpers for location nodes, family members, categories, attribute definitions, attribute options, and item statuses.
- Modify `frontend/src/stores/configuration.ts`: add store actions that call the new API helpers and reload the bootstrap payload.
- Modify `frontend/src/components/config/ResidenceLocationPanel.vue`: add location-node edit dialog and tree actions.
- Modify `frontend/src/components/config/FamilyMemberPanel.vue`: add family-member edit dialog and active status display.
- Modify `frontend/src/components/config/CategoryFieldPanel.vue`: add category edit, attribute-definition edit, and attribute-option create/edit workflows.
- Modify `frontend/src/components/config/DictionaryPanel.vue`: add item-status create/edit workflow; keep dictionary groups/options read-only.
- Create `frontend/tests/config-management-contract.ts`: type-level API/store contract tests.
- Create `frontend/tests/config-management-ui-contract.mjs`: source-level UI wiring checks.

## Task 1: Add Frontend Type Contract Tests

**Files:**
- Create: `frontend/tests/config-management-contract.ts`

- [ ] **Step 1: Write the failing type contract**

Create `frontend/tests/config-management-contract.ts`:

```ts
import {
  createAttributeOptionApi,
  createItemStatusApi,
  updateAttributeDefinitionApi,
  updateAttributeOptionApi,
  updateCategoryApi,
  updateFamilyMemberApi,
  updateItemStatusApi,
  updateLocationNodeApi,
  type AttributeDefinition,
  type AttributeDefinitionUpdate,
  type AttributeOption,
  type AttributeOptionCreate,
  type AttributeOptionUpdate,
  type Category,
  type CategoryUpdate,
  type FamilyMember,
  type FamilyMemberUpdate,
  type ItemStatus,
  type ItemStatusCreate,
  type ItemStatusUpdate,
  type LocationNode,
  type LocationNodeUpdate
} from '../src/api/configuration'
import { useConfigurationStore } from '../src/stores/configuration'

function expectType<T>(_value: T): void {}

const locationUpdatePayload: LocationNodeUpdate = {
  parent_id: null,
  name: 'Shelf A',
  node_type: 'shelf',
  icon: 'shelf',
  sort_order: 10,
  note: 'Updated location',
  is_active: false
}

const memberUpdatePayload: FamilyMemberUpdate = {
  name: 'Alex',
  relation: 'Owner',
  phone: '123',
  note: 'Updated member',
  is_active: true
}

const categoryUpdatePayload: CategoryUpdate = {
  parent_id: null,
  name: 'Important documents',
  icon: 'document',
  sort_order: 20,
  is_active: true
}

const definitionUpdatePayload: AttributeDefinitionUpdate = {
  name: 'Expiration date',
  field_type: 'date',
  default_value: '',
  privacy_level: 'normal',
  is_required: true,
  is_filterable: true,
  sort_order: 30,
  is_active: true
}

const optionCreatePayload: AttributeOptionCreate = {
  definition_id: 1,
  label: 'Permanent',
  value: 'permanent',
  sort_order: 10
}

const optionUpdatePayload: AttributeOptionUpdate = {
  label: 'Long term',
  sort_order: 20,
  is_active: false
}

const itemStatusCreatePayload: ItemStatusCreate = {
  code: 'reserved',
  name: 'Reserved',
  semantic: 'available',
  sort_order: 80
}

const itemStatusUpdatePayload: ItemStatusUpdate = {
  name: 'Reserved now',
  semantic: 'available',
  sort_order: 90,
  is_active: true
}

async function assertConfigurationApiContract() {
  expectType<LocationNode>(await updateLocationNodeApi(1, locationUpdatePayload))
  expectType<FamilyMember>(await updateFamilyMemberApi(1, memberUpdatePayload))
  expectType<Category>(await updateCategoryApi(1, categoryUpdatePayload))
  expectType<AttributeDefinition>(await updateAttributeDefinitionApi(1, definitionUpdatePayload))
  expectType<AttributeOption>(await createAttributeOptionApi(optionCreatePayload))
  expectType<AttributeOption>(await updateAttributeOptionApi(1, optionUpdatePayload))
  expectType<ItemStatus>(await createItemStatusApi(itemStatusCreatePayload))
  expectType<ItemStatus>(await updateItemStatusApi(1, itemStatusUpdatePayload))
}

async function assertConfigurationStoreContract() {
  const configuration = useConfigurationStore()

  await configuration.updateLocationNode(1, locationUpdatePayload)
  await configuration.updateFamilyMember(1, memberUpdatePayload)
  await configuration.updateCategory(1, categoryUpdatePayload)
  await configuration.updateAttributeDefinition(1, definitionUpdatePayload)
  await configuration.createAttributeOption(optionCreatePayload)
  await configuration.updateAttributeOption(1, optionUpdatePayload)
  await configuration.createItemStatus(itemStatusCreatePayload)
  await configuration.updateItemStatus(1, itemStatusUpdatePayload)
}

void assertConfigurationApiContract
void assertConfigurationStoreContract
```

- [ ] **Step 2: Run the type contract and confirm it fails**

Run from `frontend`:

```powershell
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: FAIL because the new payload types, API helpers, and store actions do not exist yet.

## Task 2: Add Source-Level UI Contract Tests

**Files:**
- Create: `frontend/tests/config-management-ui-contract.mjs`

- [ ] **Step 1: Write the failing UI source contract**

Create `frontend/tests/config-management-ui-contract.mjs`:

```js
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
  /v-model="locationEditForm\.is_active"/,
  'Location edit dialog should expose active state'
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
  /v-model="memberEditForm\.is_active"/,
  'Family member edit dialog should expose active state'
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
  /v-model="categoryEditForm\.is_active"/,
  'Category edit dialog should expose active state'
)
assert.match(
  categoryFieldPanel,
  /v-model="fieldEditForm\.is_active"/,
  'Field edit dialog should expose active state'
)
assert.match(
  categoryFieldPanel,
  /v-model="optionEditForm\.is_active"/,
  'Attribute option edit dialog should expose active state'
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
  /v-model="statusEditForm\.is_active"/,
  'Item status edit dialog should expose active state'
)
assert.doesNotMatch(
  dictionaryPanel,
  /updateDictionary(Group|Option)|dictionaryEditOpen|openDictionaryEdit/,
  'Dictionary groups and dictionary options should remain read-only in this slice'
)
```

- [ ] **Step 2: Run the UI contract and confirm it fails**

Run from `frontend`:

```powershell
node .\tests\config-management-ui-contract.mjs
```

Expected: FAIL because the panels do not expose these edit flows yet.

## Task 3: Implement Configuration API and Store Actions

**Files:**
- Modify: `frontend/src/api/configuration.ts`
- Modify: `frontend/src/stores/configuration.ts`
- Test: `frontend/tests/config-management-contract.ts`

- [ ] **Step 1: Add payload types**

In `frontend/src/api/configuration.ts`, add these interfaces near the existing create/update interfaces:

```ts
export interface LocationNodeUpdate {
  parent_id: number | null
  name: string
  node_type: string
  icon: string
  sort_order: number
  note: string
  is_active: boolean
}

export interface FamilyMemberUpdate {
  name: string
  relation: string
  phone: string
  note: string
  is_active: boolean
}

export interface CategoryUpdate {
  parent_id: number | null
  name: string
  icon: string
  sort_order: number
  is_active: boolean
}

export interface AttributeDefinitionUpdate {
  name: string
  field_type: string
  default_value: string
  privacy_level: string
  is_required: boolean
  is_filterable: boolean
  sort_order: number
  is_active: boolean
}

export interface AttributeOptionCreate {
  definition_id: number
  label: string
  value: string
  sort_order?: number
}

export interface AttributeOptionUpdate {
  label: string
  sort_order: number
  is_active: boolean
}

export interface ItemStatusCreate {
  code: string
  name: string
  semantic: string
  sort_order?: number
}

export interface ItemStatusUpdate {
  name: string
  semantic: string
  sort_order: number
  is_active: boolean
}
```

- [ ] **Step 2: Add API helpers**

In `frontend/src/api/configuration.ts`, add these helpers after the matching create helpers:

```ts
export async function updateLocationNodeApi(
  nodeId: number,
  payload: LocationNodeUpdate
): Promise<LocationNode> {
  const response = await apiClient.patch<LocationNode>(`/config/location-nodes/${nodeId}`, payload)
  return response.data
}

export async function updateFamilyMemberApi(
  memberId: number,
  payload: FamilyMemberUpdate
): Promise<FamilyMember> {
  const response = await apiClient.patch<FamilyMember>(`/config/family-members/${memberId}`, payload)
  return response.data
}

export async function updateCategoryApi(
  categoryId: number,
  payload: CategoryUpdate
): Promise<Category> {
  const response = await apiClient.patch<Category>(`/config/categories/${categoryId}`, payload)
  return response.data
}

export async function updateAttributeDefinitionApi(
  definitionId: number,
  payload: AttributeDefinitionUpdate
): Promise<AttributeDefinition> {
  const response = await apiClient.patch<AttributeDefinition>(
    `/config/attribute-definitions/${definitionId}`,
    payload
  )
  return response.data
}

export async function createAttributeOptionApi(
  payload: AttributeOptionCreate
): Promise<AttributeOption> {
  const response = await apiClient.post<AttributeOption>('/config/attribute-options', payload)
  return response.data
}

export async function updateAttributeOptionApi(
  optionId: number,
  payload: AttributeOptionUpdate
): Promise<AttributeOption> {
  const response = await apiClient.patch<AttributeOption>(`/config/attribute-options/${optionId}`, payload)
  return response.data
}

export async function createItemStatusApi(payload: ItemStatusCreate): Promise<ItemStatus> {
  const response = await apiClient.post<ItemStatus>('/config/item-statuses', payload)
  return response.data
}

export async function updateItemStatusApi(
  statusId: number,
  payload: ItemStatusUpdate
): Promise<ItemStatus> {
  const response = await apiClient.patch<ItemStatus>(`/config/item-statuses/${statusId}`, payload)
  return response.data
}
```

- [ ] **Step 3: Add store imports**

In `frontend/src/stores/configuration.ts`, extend imports with the new helpers and types:

```ts
  createAttributeOptionApi,
  createItemStatusApi,
  updateAttributeDefinitionApi,
  updateAttributeOptionApi,
  updateCategoryApi,
  updateFamilyMemberApi,
  updateItemStatusApi,
  updateLocationNodeApi,
```

and:

```ts
  type AttributeDefinitionUpdate,
  type AttributeOptionCreate,
  type AttributeOptionUpdate,
  type CategoryUpdate,
  type FamilyMemberUpdate,
  type ItemStatusCreate,
  type ItemStatusUpdate,
  type LocationNodeUpdate,
```

- [ ] **Step 4: Add store actions**

In the Pinia actions object, add:

```ts
    async updateLocationNode(nodeId: number, payload: LocationNodeUpdate) {
      await updateLocationNodeApi(nodeId, payload)
      await this.load()
    },
    async updateFamilyMember(memberId: number, payload: FamilyMemberUpdate) {
      await updateFamilyMemberApi(memberId, payload)
      await this.load()
    },
    async updateCategory(categoryId: number, payload: CategoryUpdate) {
      await updateCategoryApi(categoryId, payload)
      await this.load()
    },
    async updateAttributeDefinition(definitionId: number, payload: AttributeDefinitionUpdate) {
      await updateAttributeDefinitionApi(definitionId, payload)
      await this.load()
    },
    async createAttributeOption(payload: AttributeOptionCreate) {
      await createAttributeOptionApi(payload)
      await this.load()
    },
    async updateAttributeOption(optionId: number, payload: AttributeOptionUpdate) {
      await updateAttributeOptionApi(optionId, payload)
      await this.load()
    },
    async createItemStatus(payload: ItemStatusCreate) {
      await createItemStatusApi(payload)
      await this.load()
    },
    async updateItemStatus(statusId: number, payload: ItemStatusUpdate) {
      await updateItemStatusApi(statusId, payload)
      await this.load()
    }
```

- [ ] **Step 5: Run the type contract**

Run from `frontend`:

```powershell
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: PASS for `config-management-contract.ts`. If Vue component errors appear from panel tasks that have not run, fix only the data-layer issues in this task.

- [ ] **Step 6: Commit the data layer**

```powershell
git add frontend/src/api/configuration.ts frontend/src/stores/configuration.ts frontend/tests/config-management-contract.ts
git commit -m "feat: add configuration management data actions"
```

## Task 4: Add Location Node Editing

**Files:**
- Modify: `frontend/src/components/config/ResidenceLocationPanel.vue`
- Test: `frontend/tests/config-management-ui-contract.mjs`

- [ ] **Step 1: Add edit state and helpers**

In `ResidenceLocationPanel.vue`, keep the existing residence editor and add this location edit state:

```ts
const locationEditFormRef = ref<FormInstance>()
const locationEditOpen = ref(false)
const editingLocation = ref<LocationNode | null>(null)
const locationEditSaving = ref(false)

const locationEditForm = reactive({
  parent_id: null as number | null,
  name: '',
  node_type: 'room',
  icon: '',
  sort_order: 0,
  note: '',
  is_active: true
})
```

Update `TreeNode` so location nodes keep the source record:

```ts
interface TreeNode {
  id: string
  label: string
  location?: LocationNode
  children?: TreeNode[]
}
```

Add helper functions:

```ts
function collectLocationIds(node: LocationNode): Set<number> {
  const ids = new Set<number>([node.id])
  for (const child of node.children ?? []) {
    for (const childId of collectLocationIds(child)) {
      ids.add(childId)
    }
  }
  return ids
}

function flattenLocationOptions(nodes: LocationNode[], excludedIds = new Set<number>(), depth = 0): LocationOption[] {
  return nodes.flatMap((node) => {
    if (excludedIds.has(node.id)) return []
    return [
      { id: node.id, label: `${'  '.repeat(depth)}${node.name}` },
      ...flattenLocationOptions(node.children ?? [], excludedIds, depth + 1)
    ]
  })
}
```

Replace the current parent option flattening with `flattenLocationOptions(currentResidenceLocations.value)`.

Add edit parent options:

```ts
const locationEditParentOptions = computed<LocationOption[]>(() => {
  if (!editingLocation.value) return []
  const residenceNodes = locationTree.value.filter(
    (node) => node.residence_id === editingLocation.value?.residence_id
  )
  return flattenLocationOptions(residenceNodes, collectLocationIds(editingLocation.value))
})
```

- [ ] **Step 2: Add open, clear, trim, and save functions**

Add:

```ts
function trimLocationEditForm() {
  locationEditForm.name = locationEditForm.name.trim()
  locationEditForm.icon = locationEditForm.icon.trim()
  locationEditForm.note = locationEditForm.note.trim()
}

function openLocationEdit(location: LocationNode) {
  editingLocation.value = location
  Object.assign(locationEditForm, {
    parent_id: location.parent_id,
    name: location.name,
    node_type: location.node_type,
    icon: location.icon,
    sort_order: location.sort_order,
    note: location.note,
    is_active: location.is_active
  })
  locationEditOpen.value = true
}

function clearLocationEdit() {
  editingLocation.value = null
  Object.assign(locationEditForm, {
    parent_id: null,
    name: '',
    node_type: 'room',
    icon: '',
    sort_order: 0,
    note: '',
    is_active: true
  })
}

async function updateLocationNode() {
  trimLocationEditForm()
  const valid = await validateForm(locationEditFormRef.value)
  if (!valid || !editingLocation.value) return

  locationEditSaving.value = true
  try {
    await configuration.updateLocationNode(editingLocation.value.id, {
      parent_id: locationEditForm.parent_id,
      name: locationEditForm.name.trim(),
      node_type: locationEditForm.node_type,
      icon: locationEditForm.icon.trim(),
      sort_order: Number(locationEditForm.sort_order) || 0,
      note: locationEditForm.note.trim(),
      is_active: locationEditForm.is_active
    })
    locationEditOpen.value = false
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    locationEditSaving.value = false
  }
}
```

- [ ] **Step 3: Wire tree actions and dialog**

Update `toTreeNodes` so each location node includes `location: node`.

Add a default slot to `el-tree`:

```vue
<template #default="{ data: nodeData }">
  <div class="tree-node-row">
    <span>{{ nodeData.label }}</span>
    <el-tag v-if="nodeData.location" size="small" :type="nodeData.location.is_active ? 'success' : 'info'">
      {{ nodeData.location.is_active ? '启用' : '停用' }}
    </el-tag>
    <el-button
      v-if="nodeData.location"
      text
      type="primary"
      :icon="Edit"
      @click.stop="openLocationEdit(nodeData.location)"
    >
      编辑
    </el-button>
  </div>
</template>
```

Add an `el-dialog` bound to `locationEditOpen` with inputs for parent, name, node type, icon, sort order, note, and `v-model="locationEditForm.is_active"`. The save button must call `updateLocationNode`.

Add CSS:

```css
.tree-node-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
```

- [ ] **Step 4: Run focused UI contract**

Run from `frontend`:

```powershell
node .\tests\config-management-ui-contract.mjs
```

Expected: still FAIL for member/category/status flows, but location assertions should pass.

- [ ] **Step 5: Commit location editing**

```powershell
git add frontend/src/components/config/ResidenceLocationPanel.vue frontend/tests/config-management-ui-contract.mjs
git commit -m "feat: edit location nodes from configuration"
```

## Task 5: Add Family Member Editing

**Files:**
- Modify: `frontend/src/components/config/FamilyMemberPanel.vue`
- Test: `frontend/tests/config-management-ui-contract.mjs`

- [ ] **Step 1: Add edit state**

Update imports to include `Edit` and the `FamilyMember` type:

```ts
import { Edit, Plus } from '@element-plus/icons-vue'
import type { FamilyMember } from '../../api/configuration'
```

Add:

```ts
const memberEditFormRef = ref<FormInstance>()
const memberEditOpen = ref(false)
const editingMember = ref<FamilyMember | null>(null)
const memberEditSaving = ref(false)

const memberEditForm = reactive({
  name: '',
  relation: '',
  phone: '',
  note: '',
  is_active: true
})
```

- [ ] **Step 2: Add edit functions**

Add:

```ts
function trimMemberEditForm() {
  memberEditForm.name = memberEditForm.name.trim()
  memberEditForm.relation = memberEditForm.relation.trim()
  memberEditForm.phone = memberEditForm.phone.trim()
  memberEditForm.note = memberEditForm.note.trim()
}

function openMemberEdit(member: FamilyMember) {
  editingMember.value = member
  Object.assign(memberEditForm, {
    name: member.name,
    relation: member.relation,
    phone: member.phone,
    note: member.note,
    is_active: member.is_active
  })
  memberEditOpen.value = true
}

function clearMemberEdit() {
  editingMember.value = null
  Object.assign(memberEditForm, {
    name: '',
    relation: '',
    phone: '',
    note: '',
    is_active: true
  })
}

async function updateFamilyMember() {
  trimMemberEditForm()
  const valid = await validateForm(memberEditFormRef.value)
  if (!valid || !editingMember.value) return

  memberEditSaving.value = true
  try {
    await configuration.updateFamilyMember(editingMember.value.id, {
      name: memberEditForm.name.trim(),
      relation: memberEditForm.relation.trim(),
      phone: memberEditForm.phone.trim(),
      note: memberEditForm.note.trim(),
      is_active: memberEditForm.is_active
    })
    memberEditOpen.value = false
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    memberEditSaving.value = false
  }
}
```

- [ ] **Step 3: Add table status, action, and dialog**

Add `is_active` and action columns to the member table. The action button calls `openMemberEdit(row)` and uses `:icon="Edit"`.

Add an edit dialog bound to `memberEditOpen` with inputs for name, relation, phone, note, and `v-model="memberEditForm.is_active"`. The save button calls `updateFamilyMember`.

- [ ] **Step 4: Run focused UI contract**

Run from `frontend`:

```powershell
node .\tests\config-management-ui-contract.mjs
```

Expected: still FAIL for category/status flows, but member assertions should pass.

- [ ] **Step 5: Commit member editing**

```powershell
git add frontend/src/components/config/FamilyMemberPanel.vue
git commit -m "feat: edit family members from configuration"
```

## Task 6: Add Category, Field, and Attribute Option Editing

**Files:**
- Modify: `frontend/src/components/config/CategoryFieldPanel.vue`
- Test: `frontend/tests/config-management-ui-contract.mjs`

- [ ] **Step 1: Add imports and state**

Update imports:

```ts
import { CirclePlus, Edit, Plus } from '@element-plus/icons-vue'
import type { AttributeDefinition, AttributeOption, Category } from '../../api/configuration'
```

Add refs and forms:

```ts
const categoryEditFormRef = ref<FormInstance>()
const fieldEditFormRef = ref<FormInstance>()
const optionFormRef = ref<FormInstance>()
const optionEditFormRef = ref<FormInstance>()
const categoryEditOpen = ref(false)
const fieldEditOpen = ref(false)
const optionEditOpen = ref(false)
const editingCategory = ref<Category | null>(null)
const editingField = ref<AttributeDefinition | null>(null)
const editingOption = ref<AttributeOption | null>(null)
const categoryEditSaving = ref(false)
const fieldEditSaving = ref(false)
const optionSaving = ref(false)
const optionEditSaving = ref(false)

const categoryEditForm = reactive({
  parent_id: null as number | null,
  name: '',
  icon: '',
  sort_order: 0,
  is_active: true
})

const fieldEditForm = reactive({
  name: '',
  field_type: 'text',
  default_value: '',
  privacy_level: 'normal',
  is_required: false,
  is_filterable: false,
  sort_order: 0,
  is_active: true
})

const optionForm = reactive({
  definition_id: undefined as number | undefined,
  label: '',
  value: '',
  sort_order: 0
})

const optionEditForm = reactive({
  label: '',
  sort_order: 0,
  is_active: true
})
```

Add:

```ts
const selectFieldTypes = new Set(['single_select', 'multi_select'])
const selectableAttributeDefinitions = computed(() =>
  selectedCategoryFields.value.filter((field) => selectFieldTypes.has(field.field_type))
)
```

- [ ] **Step 2: Add category parent exclusion helpers**

Add:

```ts
function collectCategoryIds(category: Category): Set<number> {
  const ids = new Set<number>([category.id])
  for (const child of category.children ?? []) {
    for (const childId of collectCategoryIds(child)) {
      ids.add(childId)
    }
  }
  return ids
}

function flattenCategoryOptions(nodes: Category[], excludedIds = new Set<number>(), depth = 0): CategoryOption[] {
  return nodes.flatMap((node) => {
    if (excludedIds.has(node.id)) return []
    return [
      { id: node.id, label: `${'  '.repeat(depth)}${node.name}` },
      ...flattenCategoryOptions(node.children ?? [], excludedIds, depth + 1)
    ]
  })
}

const categoryEditParentOptions = computed<CategoryOption[]>(() =>
  flattenCategoryOptions(
    categories.value,
    editingCategory.value ? collectCategoryIds(editingCategory.value) : new Set<number>()
  )
)
```

Use `flattenCategoryOptions(categories.value)` for the create form category options.

- [ ] **Step 3: Add category edit functions**

Add:

```ts
function trimCategoryEditForm() {
  categoryEditForm.name = categoryEditForm.name.trim()
  categoryEditForm.icon = categoryEditForm.icon.trim()
}

function openCategoryEdit(category: Category) {
  editingCategory.value = category
  Object.assign(categoryEditForm, {
    parent_id: category.parent_id,
    name: category.name,
    icon: category.icon,
    sort_order: category.sort_order,
    is_active: category.is_active
  })
  categoryEditOpen.value = true
}

function clearCategoryEdit() {
  editingCategory.value = null
  Object.assign(categoryEditForm, {
    parent_id: null,
    name: '',
    icon: '',
    sort_order: 0,
    is_active: true
  })
}

async function updateCategory() {
  trimCategoryEditForm()
  const valid = await validateForm(categoryEditFormRef.value)
  if (!valid || !editingCategory.value) return

  categoryEditSaving.value = true
  try {
    await configuration.updateCategory(editingCategory.value.id, {
      parent_id: categoryEditForm.parent_id,
      name: categoryEditForm.name.trim(),
      icon: categoryEditForm.icon.trim(),
      sort_order: Number(categoryEditForm.sort_order) || 0,
      is_active: categoryEditForm.is_active
    })
    categoryEditOpen.value = false
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    categoryEditSaving.value = false
  }
}
```

- [ ] **Step 4: Add field edit functions**

Add:

```ts
function trimFieldEditForm() {
  fieldEditForm.name = fieldEditForm.name.trim()
  fieldEditForm.default_value = fieldEditForm.default_value.trim()
  fieldEditForm.privacy_level = fieldEditForm.privacy_level.trim()
}

function openFieldEdit(field: AttributeDefinition) {
  editingField.value = field
  Object.assign(fieldEditForm, {
    name: field.name,
    field_type: field.field_type,
    default_value: field.default_value,
    privacy_level: field.privacy_level,
    is_required: field.is_required,
    is_filterable: field.is_filterable,
    sort_order: field.sort_order,
    is_active: field.is_active
  })
  fieldEditOpen.value = true
}

function clearFieldEdit() {
  editingField.value = null
  Object.assign(fieldEditForm, {
    name: '',
    field_type: 'text',
    default_value: '',
    privacy_level: 'normal',
    is_required: false,
    is_filterable: false,
    sort_order: 0,
    is_active: true
  })
}

async function updateAttributeDefinition() {
  trimFieldEditForm()
  const valid = await validateForm(fieldEditFormRef.value)
  if (!valid || !editingField.value) return

  fieldEditSaving.value = true
  try {
    await configuration.updateAttributeDefinition(editingField.value.id, {
      name: fieldEditForm.name.trim(),
      field_type: fieldEditForm.field_type,
      default_value: fieldEditForm.default_value.trim(),
      privacy_level: fieldEditForm.privacy_level.trim() || 'normal',
      is_required: fieldEditForm.is_required,
      is_filterable: fieldEditForm.is_filterable,
      sort_order: Number(fieldEditForm.sort_order) || 0,
      is_active: fieldEditForm.is_active
    })
    fieldEditOpen.value = false
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    fieldEditSaving.value = false
  }
}
```

- [ ] **Step 5: Add attribute option create and edit functions**

Add:

```ts
function trimOptionForm() {
  optionForm.label = optionForm.label.trim()
  optionForm.value = optionForm.value.trim()
}

function trimOptionEditForm() {
  optionEditForm.label = optionEditForm.label.trim()
}

function openOptionEdit(option: AttributeOption) {
  editingOption.value = option
  Object.assign(optionEditForm, {
    label: option.label,
    sort_order: option.sort_order,
    is_active: option.is_active
  })
  optionEditOpen.value = true
}

function clearOptionEdit() {
  editingOption.value = null
  Object.assign(optionEditForm, {
    label: '',
    sort_order: 0,
    is_active: true
  })
}

async function saveAttributeOption() {
  trimOptionForm()
  const valid = await validateForm(optionFormRef.value)
  if (!valid || !optionForm.definition_id) return

  optionSaving.value = true
  try {
    await configuration.createAttributeOption({
      definition_id: optionForm.definition_id,
      label: optionForm.label.trim(),
      value: optionForm.value.trim(),
      sort_order: Number(optionForm.sort_order) || 0
    })
    Object.assign(optionForm, { label: '', value: '', sort_order: 0 })
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    optionSaving.value = false
  }
}

async function updateAttributeOption() {
  trimOptionEditForm()
  const valid = await validateForm(optionEditFormRef.value)
  if (!valid || !editingOption.value) return

  optionEditSaving.value = true
  try {
    await configuration.updateAttributeOption(editingOption.value.id, {
      label: optionEditForm.label.trim(),
      sort_order: Number(optionEditForm.sort_order) || 0,
      is_active: optionEditForm.is_active
    })
    optionEditOpen.value = false
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    optionEditSaving.value = false
  }
}
```

- [ ] **Step 6: Wire category, field, and option UI**

Add category table columns for `is_active` and actions. The edit button must call `openCategoryEdit(row)`.

Add field table columns for `is_active` and actions. The edit button must call `openFieldEdit(row)`.

Add an attribute option form below the selected field table. Bind the field selector to `optionForm.definition_id`, using `selectableAttributeDefinitions`. The save button calls `saveAttributeOption`.

Add an expanded or nested option table for each selected field row. Each option row shows label, value, active state, and an edit button that calls `openOptionEdit(option)`.

Add three dialogs:

- category dialog bound to `categoryEditOpen` with parent, name, icon, sort order, and `v-model="categoryEditForm.is_active"`;
- field dialog bound to `fieldEditOpen` with name, type, default value, privacy level, required, filterable, sort order, and `v-model="fieldEditForm.is_active"`;
- option dialog bound to `optionEditOpen` with label, read-only value display, sort order, and `v-model="optionEditForm.is_active"`.

- [ ] **Step 7: Run focused UI contract**

Run from `frontend`:

```powershell
node .\tests\config-management-ui-contract.mjs
```

Expected: still FAIL for item status flow only; category, field, and option assertions should pass.

- [ ] **Step 8: Commit category and field editing**

```powershell
git add frontend/src/components/config/CategoryFieldPanel.vue
git commit -m "feat: edit categories and custom fields"
```

## Task 7: Add Item Status Management

**Files:**
- Modify: `frontend/src/components/config/DictionaryPanel.vue`
- Test: `frontend/tests/config-management-ui-contract.mjs`

- [ ] **Step 1: Add imports and state**

Update imports:

```ts
import { computed, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, type FormInstance } from 'element-plus'
import { Edit, Plus } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../../api/client'
import type { ItemStatus } from '../../api/configuration'
import { useConfigurationStore } from '../../stores/configuration'
```

Add:

```ts
const statusFormRef = ref<FormInstance>()
const statusEditFormRef = ref<FormInstance>()
const statusSaving = ref(false)
const statusEditSaving = ref(false)
const statusEditOpen = ref(false)
const editingStatus = ref<ItemStatus | null>(null)

const statusForm = reactive({
  code: '',
  name: '',
  semantic: 'available',
  sort_order: 0
})

const statusEditForm = reactive({
  name: '',
  semantic: 'available',
  sort_order: 0,
  is_active: true
})

const statusSemanticOptions = ['available', 'away', 'removed', 'missing']
```

- [ ] **Step 2: Add status functions**

Add:

```ts
async function validateForm(form?: FormInstance) {
  if (!form) return false
  return form.validate().then(() => true).catch(() => false)
}

function trimStatusForm() {
  statusForm.code = statusForm.code.trim()
  statusForm.name = statusForm.name.trim()
  statusForm.semantic = statusForm.semantic.trim()
}

function trimStatusEditForm() {
  statusEditForm.name = statusEditForm.name.trim()
  statusEditForm.semantic = statusEditForm.semantic.trim()
}

function openStatusEdit(status: ItemStatus) {
  editingStatus.value = status
  Object.assign(statusEditForm, {
    name: status.name,
    semantic: status.semantic,
    sort_order: status.sort_order,
    is_active: status.is_active
  })
  statusEditOpen.value = true
}

function clearStatusEdit() {
  editingStatus.value = null
  Object.assign(statusEditForm, {
    name: '',
    semantic: 'available',
    sort_order: 0,
    is_active: true
  })
}

async function saveItemStatus() {
  trimStatusForm()
  const valid = await validateForm(statusFormRef.value)
  if (!valid) return

  statusSaving.value = true
  try {
    await configuration.createItemStatus({
      code: statusForm.code.trim(),
      name: statusForm.name.trim(),
      semantic: statusForm.semantic.trim(),
      sort_order: Number(statusForm.sort_order) || 0
    })
    Object.assign(statusForm, { code: '', name: '', semantic: 'available', sort_order: 0 })
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    statusSaving.value = false
  }
}

async function updateItemStatus() {
  trimStatusEditForm()
  const valid = await validateForm(statusEditFormRef.value)
  if (!valid || !editingStatus.value) return

  statusEditSaving.value = true
  try {
    await configuration.updateItemStatus(editingStatus.value.id, {
      name: statusEditForm.name.trim(),
      semantic: statusEditForm.semantic.trim(),
      sort_order: Number(statusEditForm.sort_order) || 0,
      is_active: statusEditForm.is_active
    })
    statusEditOpen.value = false
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    statusEditSaving.value = false
  }
}
```

- [ ] **Step 3: Add status create/edit UI while keeping dictionaries read-only**

Add a compact status create form above the status table. It includes code, name, semantic select, sort order, and a save button that calls `saveItemStatus`.

Add status table columns for `is_active` and actions. The edit button calls `openStatusEdit(row)` and uses `:icon="Edit"`.

Add a status edit dialog bound to `statusEditOpen` with read-only code display, name, semantic select, sort order, and `v-model="statusEditForm.is_active"`. The save button calls `updateItemStatus`.

Do not add dictionary group or dictionary option edit functions, dialogs, or update store calls.

- [ ] **Step 4: Run UI contract**

Run from `frontend`:

```powershell
node .\tests\config-management-ui-contract.mjs
```

Expected: PASS.

- [ ] **Step 5: Commit item status management**

```powershell
git add frontend/src/components/config/DictionaryPanel.vue frontend/tests/config-management-ui-contract.mjs
git commit -m "feat: manage item statuses"
```

## Task 8: Final Verification and Integration

**Files:**
- Verify all files touched in Tasks 1-7.

- [ ] **Step 1: Run frontend type contract**

Run from `frontend`:

```powershell
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: PASS.

- [ ] **Step 2: Run frontend source contracts**

Run from `frontend`:

```powershell
node .\tests\config-management-ui-contract.mjs
node .\tests\admin-users-ui-contract.mjs
node .\tests\audit-contract.mjs
node .\tests\audit-logs-store-runtime.mjs
```

Expected: all PASS. The audit runtime may print the existing Vite websocket port warning; the command must exit 0.

- [ ] **Step 3: Run frontend build**

Run from `frontend`:

```powershell
npm.cmd run build
```

Expected: PASS. Existing Vite/Rollup warnings about pure annotations or chunk size are acceptable if the build exits 0.

- [ ] **Step 4: Run focused backend configuration tests**

Run from `backend`:

```powershell
python -m pytest tests/test_configuration_api.py::test_admin_can_use_backend_configuration_write_contract_routes tests/test_configuration_api.py::test_viewer_cannot_create_configuration -v
```

Expected: PASS.

- [ ] **Step 5: Run diff hygiene check**

Run from repo root:

```powershell
git diff --check
```

Expected: PASS or only pre-existing CRLF warnings that do not point to newly introduced trailing whitespace.

- [ ] **Step 6: Inspect worktree**

Run from repo root:

```powershell
git status --short --branch
```

Expected: branch shows local commits ahead of origin and no unstaged/untracked implementation files after the final commit.

- [ ] **Step 7: Push after implementation is complete**

Run from repo root after all implementation commits are present:

```powershell
git push origin phase-1-foundation
```

Expected: push succeeds and origin matches the local branch.
