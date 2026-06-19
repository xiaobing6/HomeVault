from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.auth import User
from app.schemas.inventory import (
    ArchiveItemRequest,
    ChangeStatusRequest,
    ItemAttachmentResponse,
    ItemCreate,
    ItemDetailResponse,
    ItemImageResponse,
    ItemImageUpdate,
    ItemListQuery,
    ItemListResponse,
    ItemMovementResponse,
    ItemQuantityChangeResponse,
    ItemUpdate,
    LoanCreate,
    LoanReturn,
    MoveItemRequest,
    QuantityAdjustmentCreate,
    TagCreate,
    TagResponse,
)
from app.services.inventory import (
    add_item_attachment,
    add_item_image,
    adjust_quantity,
    archive_item,
    archive_item_attachment,
    archive_item_image,
    change_item_status,
    create_item,
    create_loan,
    create_tag,
    get_item_detail,
    list_items,
    list_movements,
    list_quantity_changes,
    list_tags,
    move_item,
    return_loan,
    update_item,
    update_item_image_metadata,
)

READ_PERMISSION = "items:view"
CREATE_PERMISSION = "items:create"
EDIT_PERMISSION = "items:edit"
ARCHIVE_PERMISSION = "items:archive"

router = APIRouter(tags=["inventory"])


@router.get("/items", response_model=ItemListResponse)
def items(
    query: ItemListQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(READ_PERMISSION)),
) -> ItemListResponse:
    return list_items(db, query)


@router.post("/items", response_model=ItemDetailResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    payload: ItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(CREATE_PERMISSION)),
) -> ItemDetailResponse:
    return create_item(db, payload, actor_id=user.id)


@router.get("/items/{item_id}", response_model=ItemDetailResponse)
def item_detail(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(READ_PERMISSION)),
) -> ItemDetailResponse:
    return get_item_detail(db, item_id)


@router.patch("/items/{item_id}", response_model=ItemDetailResponse)
def update_inventory_item(
    item_id: int,
    payload: ItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemDetailResponse:
    return update_item(db, item_id, payload, actor_id=user.id)


@router.post("/items/{item_id}/archive", response_model=ItemDetailResponse)
def archive_inventory_item(
    item_id: int,
    payload: ArchiveItemRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(ARCHIVE_PERMISSION)),
) -> ItemDetailResponse:
    return archive_item(db, item_id, payload, actor_id=user.id)


@router.post("/items/{item_id}/move", response_model=ItemDetailResponse)
def move_inventory_item(
    item_id: int,
    payload: MoveItemRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemDetailResponse:
    return move_item(db, item_id, payload, actor_id=user.id)


@router.post("/items/{item_id}/status", response_model=ItemDetailResponse)
def change_inventory_item_status(
    item_id: int,
    payload: ChangeStatusRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemDetailResponse:
    return change_item_status(db, item_id, payload, actor_id=user.id)


@router.post("/items/{item_id}/quantity-adjustments", response_model=ItemDetailResponse)
def adjust_inventory_item_quantity(
    item_id: int,
    payload: QuantityAdjustmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemDetailResponse:
    return adjust_quantity(db, item_id, payload, actor_id=user.id)


@router.get("/items/{item_id}/quantity-adjustments", response_model=list[ItemQuantityChangeResponse])
def inventory_item_quantity_adjustments(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(READ_PERMISSION)),
) -> list[ItemQuantityChangeResponse]:
    return list_quantity_changes(db, item_id)


@router.post("/items/{item_id}/loans", response_model=ItemDetailResponse)
def create_inventory_item_loan(
    item_id: int,
    payload: LoanCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemDetailResponse:
    return create_loan(db, item_id, payload, actor_id=user.id)


@router.post("/items/{item_id}/loans/{loan_id}/return", response_model=ItemDetailResponse)
def return_inventory_item_loan(
    item_id: int,
    loan_id: int,
    payload: LoanReturn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemDetailResponse:
    return return_loan(db, item_id, loan_id, payload, actor_id=user.id)


@router.get("/items/{item_id}/movements", response_model=list[ItemMovementResponse])
def inventory_item_movements(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(READ_PERMISSION)),
) -> list[ItemMovementResponse]:
    return list_movements(db, item_id)


@router.post("/items/{item_id}/images", response_model=ItemImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_inventory_item_image(
    item_id: int,
    file: UploadFile = File(...),
    is_primary: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemImageResponse:
    return await add_item_image(db, item_id, file, is_primary=is_primary, actor_id=user.id)


@router.patch("/items/{item_id}/images/{image_id}", response_model=ItemImageResponse)
def update_inventory_item_image(
    item_id: int,
    image_id: int,
    payload: ItemImageUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemImageResponse:
    return update_item_image_metadata(db, item_id, image_id, payload, actor_id=user.id)


@router.delete("/items/{item_id}/images/{image_id}", response_model=ItemDetailResponse)
def delete_inventory_item_image(
    item_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemDetailResponse:
    return archive_item_image(db, item_id, image_id, actor_id=user.id)


@router.post("/items/{item_id}/attachments", response_model=ItemAttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_inventory_item_attachment(
    item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemAttachmentResponse:
    return await add_item_attachment(db, item_id, file, actor_id=user.id)


@router.delete("/items/{item_id}/attachments/{attachment_id}", response_model=ItemDetailResponse)
def delete_inventory_item_attachment(
    item_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemDetailResponse:
    return archive_item_attachment(db, item_id, attachment_id, actor_id=user.id)


@router.get("/tags", response_model=list[TagResponse])
def tags(
    search: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(READ_PERMISSION)),
) -> list[TagResponse]:
    return list_tags(db, search=search)


@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_tag(
    payload: TagCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(CREATE_PERMISSION)),
) -> TagResponse:
    return create_tag(db, payload)
