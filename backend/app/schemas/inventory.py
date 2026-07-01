from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PrivacyLevel = Literal["normal", "sensitive"]


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RequestModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class PlacementPayload(RequestModel):
    location_node_id: int | None = None
    container_item_id: int | None = None

    @model_validator(mode="after")
    def validate_single_placement(self) -> PlacementPayload:
        if self.location_node_id is not None and self.container_item_id is not None:
            raise ValueError("请选择位置或容器，不能同时选择两者")
        return self


class ItemAttributeValueInput(RequestModel):
    attribute_definition_id: int
    value: str = ""


class ItemCreate(PlacementPayload):
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    category_id: int
    status_id: int
    quantity: Decimal = Decimal("1")
    unit: str = "件"
    importance: str = Field(default="medium", max_length=40)
    owner_member_id: int | None = None
    keeper_member_id: int | None = None
    is_container: bool = False
    privacy_level: PrivacyLevel = "normal"
    attribute_values: list[ItemAttributeValueInput] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ItemUpdate(RequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    category_id: int | None = None
    unit: str | None = None
    importance: str | None = Field(default=None, max_length=40)
    owner_member_id: int | None = None
    keeper_member_id: int | None = None
    is_container: bool | None = None
    privacy_level: PrivacyLevel | None = None
    attribute_values: list[ItemAttributeValueInput] | None = None
    tags: list[str] | None = None


class ItemListQuery(RequestModel):
    search: str | None = None
    category_id: int | None = None
    residence_id: int | None = None
    location_node_id: int | None = None
    container_item_id: int | None = None
    status_id: int | None = None
    importance: str | None = None
    tag: str | None = None
    is_on_loan: bool | None = None
    include_archived: bool = False
    owner_member_id: int | None = None
    keeper_member_id: int | None = None
    container_only: bool | None = None
    has_pending_reminder: bool | None = None
    has_upcoming_reminder: bool | None = None
    has_overdue_reminder: bool | None = None
    reminder_upcoming_days: int = Field(default=7, ge=1, le=90)
    sort: str = "updated_desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class TagResponse(ResponseModel):
    id: int
    name: str
    normalized_name: str
    created_at: datetime


class ItemAttributeValueResponse(ResponseModel):
    id: int
    attribute_definition_id: int
    attribute_key: str
    attribute_name: str
    field_type: str
    value: str


class ItemSummaryResponse(ResponseModel):
    id: int
    name: str
    description: str
    category_id: int
    category_name: str
    status_id: int
    status_name: str
    status_semantic: str
    quantity: Decimal
    unit: str
    importance: str
    owner_member_id: int | None = None
    owner_member_name: str | None = None
    keeper_member_id: int | None = None
    keeper_member_name: str | None = None
    location_node_id: int | None = None
    location_node_name: str | None = None
    residence_id: int | None = None
    residence_name: str | None = None
    container_item_id: int | None = None
    container_item_name: str | None = None
    is_container: bool
    privacy_level: PrivacyLevel
    is_archived: bool
    primary_image_url: str | None = None
    tags: list[TagResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ItemListResponse(ResponseModel):
    items: list[ItemSummaryResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int


class ItemImageResponse(ResponseModel):
    id: int
    item_id: int
    original_filename: str
    stored_filename: str
    file_path: str
    content_type: str
    byte_size: int
    is_primary: bool
    sort_order: int
    is_archived: bool
    uploaded_by_id: int | None = None
    created_at: datetime
    url: str | None = None


class ItemAttachmentResponse(ResponseModel):
    id: int
    item_id: int
    original_filename: str
    stored_filename: str
    file_path: str
    content_type: str
    byte_size: int
    is_archived: bool
    uploaded_by_id: int | None = None
    created_at: datetime
    download_url: str | None = None


class ItemMovementResponse(ResponseModel):
    id: int
    item_id: int
    previous_location_node_id: int | None = None
    previous_location_node_name: str | None = None
    new_location_node_id: int | None = None
    new_location_node_name: str | None = None
    previous_container_item_id: int | None = None
    previous_container_item_name: str | None = None
    new_container_item_id: int | None = None
    new_container_item_name: str | None = None
    previous_status_id: int | None = None
    previous_status_name: str | None = None
    new_status_id: int | None = None
    new_status_name: str | None = None
    movement_type: str
    reason: str
    note: str
    actor_id: int | None = None
    created_at: datetime


class ItemQuantityChangeResponse(ResponseModel):
    id: int
    item_id: int
    quantity_before: Decimal
    quantity_after: Decimal
    quantity_delta: Decimal
    unit: str
    reason: str
    note: str
    actor_id: int | None = None
    created_at: datetime


class ItemLoanResponse(ResponseModel):
    id: int
    item_id: int
    borrower_name: str
    borrower_contact: str
    expected_return_date: date | None = None
    loan_note: str
    loaned_at: datetime
    returned_at: datetime | None = None
    return_note: str
    return_location_node_id: int | None = None
    return_location_node_name: str | None = None
    return_container_item_id: int | None = None
    return_container_item_name: str | None = None
    loan_actor_id: int | None = None
    return_actor_id: int | None = None
    created_at: datetime
    updated_at: datetime


class ItemDetailResponse(ItemSummaryResponse):
    archive_reason: str
    archived_at: datetime | None = None
    created_by_id: int | None = None
    updated_by_id: int | None = None
    attribute_values: list[ItemAttributeValueResponse] = Field(default_factory=list)
    images: list[ItemImageResponse] = Field(default_factory=list)
    attachments: list[ItemAttachmentResponse] = Field(default_factory=list)
    movements: list[ItemMovementResponse] = Field(default_factory=list)
    quantity_changes: list[ItemQuantityChangeResponse] = Field(default_factory=list)
    loans: list[ItemLoanResponse] = Field(default_factory=list)


class MoveItemRequest(PlacementPayload):
    reason: str = Field(default="", max_length=255)
    note: str = ""


class ChangeStatusRequest(RequestModel):
    status_id: int
    reason: str = Field(default="", max_length=255)
    note: str = ""


class QuantityAdjustmentCreate(RequestModel):
    new_quantity: Decimal | None = None
    delta: Decimal | None = None
    reason: str = Field(min_length=1, max_length=255)
    note: str = ""

    @model_validator(mode="after")
    def validate_quantity_change(self) -> QuantityAdjustmentCreate:
        if self.new_quantity is None and self.delta is None:
            raise ValueError("请填写调整后的数量或变化数量")
        if self.new_quantity is not None and self.delta is not None:
            raise ValueError("请选择调整后的数量或变化数量，不能同时填写两者")
        return self


class LoanCreate(RequestModel):
    borrower_name: str = Field(min_length=1, max_length=160)
    borrower_contact: str = Field(default="", max_length=160)
    expected_return_date: date | None = None
    loan_note: str = ""


class LoanReturn(PlacementPayload):
    return_note: str = ""
    target_status_id: int | None = None


class ArchiveItemRequest(RequestModel):
    archive_reason: str = Field(default="", max_length=255)


class ItemIdBatchMixin(RequestModel):
    item_ids: list[int] = Field(min_length=1, max_length=200)

    @field_validator("item_ids")
    @classmethod
    def validate_item_ids(cls, item_ids: list[int]) -> list[int]:
        seen: set[int] = set()
        deduped: list[int] = []
        for item_id in item_ids:
            if item_id <= 0:
                raise ValueError("物品不存在")
            if item_id not in seen:
                seen.add(item_id)
                deduped.append(item_id)
        return deduped


class BulkMoveItemsRequest(ItemIdBatchMixin, PlacementPayload):
    reason: str = Field(default="", max_length=255)
    note: str = ""


class BulkChangeStatusRequest(ItemIdBatchMixin):
    status_id: int
    reason: str = Field(default="", max_length=255)
    note: str = ""


class BulkArchiveItemsRequest(ItemIdBatchMixin):
    archive_reason: str = Field(default="", max_length=255)


class BulkItemOperationResponse(ResponseModel):
    updated_count: int
    item_ids: list[int]


class ItemExportRequest(RequestModel):
    item_ids: list[int] | None = Field(default=None, max_length=200)
    filters: ItemListQuery = Field(default_factory=ItemListQuery)

    @field_validator("item_ids")
    @classmethod
    def validate_optional_item_ids(cls, item_ids: list[int] | None) -> list[int] | None:
        if item_ids is None:
            return None
        return ItemIdBatchMixin(item_ids=item_ids).item_ids


class ImportFieldMessage(ResponseModel):
    field: str
    message: str


class ImportRowPreview(ResponseModel):
    row_number: int
    original: dict[str, str] = Field(default_factory=dict)
    normalized: dict[str, object] | None = None
    errors: list[ImportFieldMessage] = Field(default_factory=list)
    warnings: list[ImportFieldMessage] = Field(default_factory=list)
    is_valid: bool


class ImportPreviewResponse(ResponseModel):
    token: str | None = None
    rows: list[ImportRowPreview] = Field(default_factory=list)
    total_count: int
    valid_count: int
    invalid_count: int


class ImportConfirmRequest(RequestModel):
    token: str = Field(min_length=1, max_length=200)


class ImportConfirmResponse(ResponseModel):
    imported_count: int
    item_ids: list[int] = Field(default_factory=list)


class ItemImageUpdate(RequestModel):
    is_primary: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)


class TagCreate(RequestModel):
    name: str = Field(min_length=1, max_length=120)


class MediaMetadataResponse(ResponseModel):
    images: list[ItemImageResponse] = Field(default_factory=list)
    attachments: list[ItemAttachmentResponse] = Field(default_factory=list)
