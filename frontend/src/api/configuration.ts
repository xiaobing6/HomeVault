import { apiClient } from './client'

export interface HomeSpace {
  id: number
  name: string
  description: string
  is_active: boolean
}

export interface Residence {
  id: number
  name: string
  description: string
  address: string
  sort_order: number
  is_active: boolean
}

export interface LocationNode {
  id: number
  residence_id: number
  parent_id: number | null
  name: string
  node_type: string
  icon: string
  sort_order: number
  note: string
  is_active: boolean
  children: LocationNode[]
}

export interface FamilyMember {
  id: number
  name: string
  relation: string
  phone: string
  note: string
  is_active: boolean
  user_id: number | null
}

export interface Category {
  id: number
  parent_id: number | null
  code: string
  name: string
  icon: string
  sort_order: number
  is_active: boolean
  attribute_definitions: AttributeDefinition[]
  children: Category[]
}

export interface AttributeOption {
  id: number
  definition_id: number
  label: string
  value: string
  sort_order: number
  is_active: boolean
}

export interface AttributeDefinition {
  id: number
  category_id: number
  key: string
  name: string
  field_type: string
  default_value: string
  privacy_level: string
  is_required: boolean
  is_filterable: boolean
  sort_order: number
  is_active: boolean
  options: AttributeOption[]
}

export interface ItemStatus {
  id: number
  code: string
  name: string
  semantic: string
  sort_order: number
  is_active: boolean
  is_system: boolean
}

export interface DictionaryOption {
  id: number
  group_id: number
  label: string
  value: string
  sort_order: number
  is_active: boolean
}

export interface DictionaryGroup {
  id: number
  code: string
  name: string
  is_system: boolean
  is_active: boolean
  options: DictionaryOption[]
}

export interface ConfigBootstrap {
  home_space: HomeSpace
  residences: Residence[]
  location_tree: LocationNode[]
  family_members: FamilyMember[]
  categories: Category[]
  item_statuses: ItemStatus[]
  dictionary_groups: DictionaryGroup[]
}

export interface ResidenceCreate {
  name: string
  description?: string
  address?: string
  sort_order?: number
}

export interface ResidenceUpdate {
  name: string
  description: string
  address: string
  sort_order: number
  is_active: boolean
}

export interface LocationNodeCreate {
  residence_id: number
  parent_id?: number | null
  name: string
  node_type?: string
  icon?: string
  sort_order?: number
  note?: string
}

export interface FamilyMemberCreate {
  name: string
  relation?: string
  phone?: string
  note?: string
}

export interface CategoryCreate {
  parent_id?: number | null
  code: string
  name: string
  icon?: string
  sort_order?: number
}

export interface AttributeDefinitionCreate {
  category_id: number
  key: string
  name: string
  field_type: string
  default_value?: string
  privacy_level?: string
  is_required?: boolean
  is_filterable?: boolean
  sort_order?: number
}

export async function fetchConfigBootstrapApi(): Promise<ConfigBootstrap> {
  const response = await apiClient.get<ConfigBootstrap>('/config/bootstrap')
  return response.data
}

export async function createResidenceApi(payload: ResidenceCreate): Promise<Residence> {
  const response = await apiClient.post<Residence>('/config/residences', payload)
  return response.data
}

export async function updateResidenceApi(
  residenceId: number,
  payload: ResidenceUpdate
): Promise<Residence> {
  const response = await apiClient.patch<Residence>(`/config/residences/${residenceId}`, payload)
  return response.data
}

export async function createLocationNodeApi(payload: LocationNodeCreate): Promise<LocationNode> {
  const response = await apiClient.post<LocationNode>('/config/location-nodes', payload)
  return response.data
}

export async function createFamilyMemberApi(payload: FamilyMemberCreate): Promise<FamilyMember> {
  const response = await apiClient.post<FamilyMember>('/config/family-members', payload)
  return response.data
}

export async function createCategoryApi(payload: CategoryCreate): Promise<Category> {
  const response = await apiClient.post<Category>('/config/categories', payload)
  return response.data
}

export async function createAttributeDefinitionApi(
  payload: AttributeDefinitionCreate
): Promise<AttributeDefinition> {
  const response = await apiClient.post<AttributeDefinition>('/config/attribute-definitions', payload)
  return response.data
}
