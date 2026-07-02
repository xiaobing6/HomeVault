import {
  createAttributeOptionApi,
  createItemStatusApi,
  updateAttributeDefinitionApi,
  updateAttributeOptionApi,
  updateCategoryApi,
  updateFamilyMemberApi,
  updateItemStatusApi,
  updateLocationNodeApi,
  updateDictionaryOptionApi,
  type AttributeDefinition,
  type AttributeDefinitionUpdate,
  type AttributeOption,
  type AttributeOptionCreate,
  type AttributeOptionUpdate,
  type Category,
  type CategoryUpdate,
  type DictionaryOption,
  type DictionaryOptionUpdate,
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

const dictionaryPayload: DictionaryOptionUpdate = {
  label: 'High value',
  sort_order: 5,
  is_active: false
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
  expectType<DictionaryOption>(await updateDictionaryOptionApi(1, dictionaryPayload))
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
  void configuration.updateDictionaryOption(1, dictionaryPayload)
}

void assertConfigurationApiContract
void assertConfigurationStoreContract
