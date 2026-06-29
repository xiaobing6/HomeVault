import { apiClient } from './client'

export type PrivacyLevel = 'normal' | 'sensitive'

export interface Tag {
  id: number
  name: string
  normalized_name: string
  created_at: string
}

export interface ItemAttributeValue {
  id: number
  attribute_definition_id: number
  attribute_key: string
  attribute_name: string
  field_type: string
  value: string
}

export interface ItemImage {
  id: number
  item_id: number
  original_filename: string
  stored_filename: string
  file_path: string
  content_type: string
  byte_size: number
  is_primary: boolean
  sort_order: number
  is_archived: boolean
  uploaded_by_id: number | null
  created_at: string
  url: string | null
}

export interface ItemAttachment {
  id: number
  item_id: number
  original_filename: string
  stored_filename: string
  file_path: string
  content_type: string
  byte_size: number
  is_archived: boolean
  uploaded_by_id: number | null
  created_at: string
  download_url: string | null
}

export interface ItemMovement {
  id: number
  item_id: number
  previous_location_node_id: number | null
  previous_location_node_name: string | null
  new_location_node_id: number | null
  new_location_node_name: string | null
  previous_container_item_id: number | null
  previous_container_item_name: string | null
  new_container_item_id: number | null
  new_container_item_name: string | null
  previous_status_id: number | null
  previous_status_name: string | null
  new_status_id: number | null
  new_status_name: string | null
  movement_type: string
  reason: string
  note: string
  actor_id: number | null
  created_at: string
}

export interface ItemQuantityChange {
  id: number
  item_id: number
  quantity_before: string
  quantity_after: string
  quantity_delta: string
  unit: string
  reason: string
  note: string
  actor_id: number | null
  created_at: string
}

export interface ItemLoan {
  id: number
  item_id: number
  borrower_name: string
  borrower_contact: string
  expected_return_date: string | null
  loan_note: string
  loaned_at: string
  returned_at: string | null
  return_note: string
  return_location_node_id: number | null
  return_location_node_name: string | null
  return_container_item_id: number | null
  return_container_item_name: string | null
  loan_actor_id: number | null
  return_actor_id: number | null
  created_at: string
  updated_at: string
}

export interface ItemSummary {
  id: number
  name: string
  description: string
  category_id: number
  category_name: string
  status_id: number
  status_name: string
  status_semantic: string
  quantity: string
  unit: string
  owner_member_id: number | null
  owner_member_name: string | null
  keeper_member_id: number | null
  keeper_member_name: string | null
  location_node_id: number | null
  location_node_name: string | null
  residence_id: number | null
  residence_name: string | null
  container_item_id: number | null
  container_item_name: string | null
  is_container: boolean
  privacy_level: PrivacyLevel
  is_archived: boolean
  primary_image_url: string | null
  tags: Tag[]
  created_at: string
  updated_at: string
}

export interface ItemDetail extends ItemSummary {
  archive_reason: string
  archived_at: string | null
  created_by_id: number | null
  updated_by_id: number | null
  attribute_values: ItemAttributeValue[]
  images: ItemImage[]
  attachments: ItemAttachment[]
  movements: ItemMovement[]
  quantity_changes: ItemQuantityChange[]
  loans: ItemLoan[]
}

export interface ItemListResponse {
  items: ItemSummary[]
  total: number
  page: number
  page_size: number
}

export interface ItemFilters {
  search?: string | null
  category_id?: number | null
  residence_id?: number | null
  location_node_id?: number | null
  container_item_id?: number | null
  status_id?: number | null
  tag?: string | null
  is_on_loan?: boolean | null
  has_pending_reminder?: boolean | null
  has_upcoming_reminder?: boolean | null
  has_overdue_reminder?: boolean | null
  reminder_upcoming_days?: number
  include_archived?: boolean
  owner_member_id?: number | null
  keeper_member_id?: number | null
  container_only?: boolean | null
  sort?: string
  page?: number
  page_size?: number
}

export interface ItemAttributeValueInput {
  attribute_definition_id: number
  value?: string
}

export interface ItemCreateRequest {
  name: string
  description?: string
  category_id: number
  status_id: number
  quantity?: string | number
  unit?: string
  owner_member_id?: number | null
  keeper_member_id?: number | null
  location_node_id?: number | null
  container_item_id?: number | null
  is_container?: boolean
  privacy_level?: PrivacyLevel
  attribute_values?: ItemAttributeValueInput[]
  tags?: string[]
}

export interface ItemUpdateRequest {
  name?: string
  description?: string | null
  category_id?: number
  unit?: string
  owner_member_id?: number | null
  keeper_member_id?: number | null
  is_container?: boolean
  privacy_level?: PrivacyLevel
  attribute_values?: ItemAttributeValueInput[] | null
  tags?: string[] | null
}

export interface MoveItemRequest {
  location_node_id?: number | null
  container_item_id?: number | null
  reason?: string
  note?: string
}

export interface ChangeStatusRequest {
  status_id: number
  reason?: string
  note?: string
}

export interface QuantityAdjustmentRequest {
  new_quantity?: string | number | null
  delta?: string | number | null
  reason: string
  note?: string
}

export interface LoanCreateRequest {
  borrower_name: string
  borrower_contact?: string
  expected_return_date?: string | null
  loan_note?: string
}

export interface LoanReturnRequest {
  location_node_id?: number | null
  container_item_id?: number | null
  return_note?: string
  target_status_id?: number | null
}

export interface ArchiveItemRequest {
  archive_reason?: string
}

export interface ItemImageUpdateRequest {
  is_primary?: boolean | null
  sort_order?: number | null
}

export interface TagCreateRequest {
  name: string
}

export async function listItemsApi(filters: ItemFilters = {}): Promise<ItemListResponse> {
  const response = await apiClient.get<ItemListResponse>('/items', { params: filters })
  return response.data
}

export async function createItemApi(payload: ItemCreateRequest): Promise<ItemDetail> {
  const response = await apiClient.post<ItemDetail>('/items', payload)
  return response.data
}

export async function fetchItemDetailApi(itemId: number): Promise<ItemDetail> {
  const response = await apiClient.get<ItemDetail>(`/items/${itemId}`)
  return response.data
}

export async function updateItemApi(itemId: number, payload: ItemUpdateRequest): Promise<ItemDetail> {
  const response = await apiClient.patch<ItemDetail>(`/items/${itemId}`, payload)
  return response.data
}

export async function archiveItemApi(
  itemId: number,
  payload: ArchiveItemRequest = {}
): Promise<ItemDetail> {
  const response = await apiClient.post<ItemDetail>(`/items/${itemId}/archive`, payload)
  return response.data
}

export async function moveItemApi(itemId: number, payload: MoveItemRequest): Promise<ItemDetail> {
  const response = await apiClient.post<ItemDetail>(`/items/${itemId}/move`, payload)
  return response.data
}

export async function changeItemStatusApi(
  itemId: number,
  payload: ChangeStatusRequest
): Promise<ItemDetail> {
  const response = await apiClient.post<ItemDetail>(`/items/${itemId}/status`, payload)
  return response.data
}

export async function adjustQuantityApi(
  itemId: number,
  payload: QuantityAdjustmentRequest
): Promise<ItemDetail> {
  const response = await apiClient.post<ItemDetail>(`/items/${itemId}/quantity-adjustments`, payload)
  return response.data
}

export async function listQuantityChangesApi(itemId: number): Promise<ItemQuantityChange[]> {
  const response = await apiClient.get<ItemQuantityChange[]>(`/items/${itemId}/quantity-adjustments`)
  return response.data
}

export async function borrowItemApi(itemId: number, payload: LoanCreateRequest): Promise<ItemDetail> {
  const response = await apiClient.post<ItemDetail>(`/items/${itemId}/loans`, payload)
  return response.data
}

export async function returnLoanApi(
  itemId: number,
  loanId: number,
  payload: LoanReturnRequest
): Promise<ItemDetail> {
  const response = await apiClient.post<ItemDetail>(`/items/${itemId}/loans/${loanId}/return`, payload)
  return response.data
}

export async function listItemMovementsApi(itemId: number): Promise<ItemMovement[]> {
  const response = await apiClient.get<ItemMovement[]>(`/items/${itemId}/movements`)
  return response.data
}

export async function uploadImageApi(
  itemId: number,
  file: File,
  isPrimary = false
): Promise<ItemImage> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('is_primary', String(isPrimary))
  const response = await apiClient.post<ItemImage>(`/items/${itemId}/images`, formData)
  return response.data
}

export async function updateImageApi(
  itemId: number,
  imageId: number,
  payload: ItemImageUpdateRequest
): Promise<ItemImage> {
  const response = await apiClient.patch<ItemImage>(`/items/${itemId}/images/${imageId}`, payload)
  return response.data
}

export async function deleteImageApi(itemId: number, imageId: number): Promise<ItemDetail> {
  const response = await apiClient.delete<ItemDetail>(`/items/${itemId}/images/${imageId}`)
  return response.data
}

export async function uploadAttachmentApi(itemId: number, file: File): Promise<ItemAttachment> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.post<ItemAttachment>(`/items/${itemId}/attachments`, formData)
  return response.data
}

export async function deleteAttachmentApi(
  itemId: number,
  attachmentId: number
): Promise<ItemDetail> {
  const response = await apiClient.delete<ItemDetail>(`/items/${itemId}/attachments/${attachmentId}`)
  return response.data
}

export async function listTagsApi(search?: string | null): Promise<Tag[]> {
  const response = await apiClient.get<Tag[]>('/tags', { params: { search } })
  return response.data
}

export async function createTagApi(payload: TagCreateRequest): Promise<Tag> {
  const response = await apiClient.post<Tag>('/tags', payload)
  return response.data
}
