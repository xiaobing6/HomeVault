from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.auth import User
from app.schemas.inventory import (
    ArchiveItemRequest,
    BulkArchiveItemsRequest,
    BulkChangeStatusRequest,
    BulkItemOperationResponse,
    BulkMoveItemsRequest,
    ChangeStatusRequest,
    ImportConfirmRequest,
    ImportConfirmResponse,
    ImportPreviewResponse,
    ItemAttachmentResponse,
    ItemCreate,
    ItemDetailResponse,
    ItemExportRequest,
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
    bulk_archive_items,
    bulk_change_item_status,
    bulk_move_items,
    change_item_status,
    create_item,
    create_loan,
    create_tag,
    export_items_csv,
    get_item_attachment_file,
    get_item_detail,
    get_item_image_file,
    list_items,
    list_movements,
    list_quantity_changes,
    list_tags,
    move_item,
    return_loan,
    update_item,
    update_item_image_metadata,
)
from app.services.inventory_import import (
    confirm_inventory_import,
    import_template_csv,
    preview_inventory_import,
    read_import_upload,
)

READ_PERMISSION = "items:view"
CREATE_PERMISSION = "items:create"
EDIT_PERMISSION = "items:edit"
ARCHIVE_PERMISSION = "items:archive"

router = APIRouter(tags=["inventory"])


def can_view_sensitive(user: User) -> bool:
    return any(role.code == "admin" for role in user.roles)


@router.get("/items", response_model=ItemListResponse)
def items(
    query: ItemListQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(READ_PERMISSION)),
) -> ItemListResponse:
    return list_items(db, query, include_sensitive=can_view_sensitive(user))


@router.post("/items", response_model=ItemDetailResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    payload: ItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(CREATE_PERMISSION)),
) -> ItemDetailResponse:
    return create_item(db, payload, actor_id=user.id, include_sensitive=can_view_sensitive(user))


@router.post("/items/bulk/move", response_model=BulkItemOperationResponse)
def bulk_move_inventory_items(
    payload: BulkMoveItemsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> BulkItemOperationResponse:
    return bulk_move_items(db, payload, actor_id=user.id)


@router.post("/items/bulk/status", response_model=BulkItemOperationResponse)
def bulk_change_inventory_item_statuses(
    payload: BulkChangeStatusRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> BulkItemOperationResponse:
    return bulk_change_item_status(db, payload, actor_id=user.id)


@router.post("/items/bulk/archive", response_model=BulkItemOperationResponse)
def bulk_archive_inventory_items(
    payload: BulkArchiveItemsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(ARCHIVE_PERMISSION)),
) -> BulkItemOperationResponse:
    return bulk_archive_items(db, payload, actor_id=user.id)


@router.post("/items/export.csv")
def export_inventory_items(
    payload: ItemExportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(READ_PERMISSION)),
) -> Response:
    content = export_items_csv(db, payload, include_sensitive=can_view_sensitive(user))
    return Response(
        content=content,
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": 'attachment; filename="homevault-items.csv"',
        },
    )


@router.get("/items/import/template.csv")
def inventory_import_template(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(CREATE_PERMISSION)),
) -> Response:
    content = import_template_csv(db)
    return Response(
        content=content,
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": 'attachment; filename="homevault-items-import-template.csv"',
        },
    )


@router.post("/items/import/preview", response_model=ImportPreviewResponse)
async def preview_inventory_items_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(CREATE_PERMISSION)),
) -> ImportPreviewResponse:
    return preview_inventory_import(db, await read_import_upload(file), user_id=user.id)


@router.post("/items/import/confirm", response_model=ImportConfirmResponse)
def confirm_inventory_items_import(
    payload: ImportConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(CREATE_PERMISSION)),
) -> ImportConfirmResponse:
    return confirm_inventory_import(db, payload.token, actor_id=user.id, user_id=user.id)


@router.get("/items/{item_id}", response_model=ItemDetailResponse)
def item_detail(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(READ_PERMISSION)),
) -> ItemDetailResponse:
    return get_item_detail(db, item_id, include_sensitive=can_view_sensitive(user))


@router.patch("/items/{item_id}", response_model=ItemDetailResponse)
def update_inventory_item(
    item_id: int,
    payload: ItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemDetailResponse:
    return update_item(db, item_id, payload, actor_id=user.id, include_sensitive=can_view_sensitive(user))


@router.post("/items/{item_id}/archive", response_model=ItemDetailResponse)
def archive_inventory_item(
    item_id: int,
    payload: ArchiveItemRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(ARCHIVE_PERMISSION)),
) -> ItemDetailResponse:
    return archive_item(db, item_id, payload, actor_id=user.id, include_sensitive=can_view_sensitive(user))


@router.post("/items/{item_id}/move", response_model=ItemDetailResponse)
def move_inventory_item(
    item_id: int,
    payload: MoveItemRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemDetailResponse:
    return move_item(db, item_id, payload, actor_id=user.id, include_sensitive=can_view_sensitive(user))


@router.post("/items/{item_id}/status", response_model=ItemDetailResponse)
def change_inventory_item_status(
    item_id: int,
    payload: ChangeStatusRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemDetailResponse:
    return change_item_status(db, item_id, payload, actor_id=user.id, include_sensitive=can_view_sensitive(user))


@router.post("/items/{item_id}/quantity-adjustments", response_model=ItemDetailResponse)
def adjust_inventory_item_quantity(
    item_id: int,
    payload: QuantityAdjustmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemDetailResponse:
    return adjust_quantity(db, item_id, payload, actor_id=user.id, include_sensitive=can_view_sensitive(user))


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
    return create_loan(db, item_id, payload, actor_id=user.id, include_sensitive=can_view_sensitive(user))


@router.post("/items/{item_id}/loans/{loan_id}/return", response_model=ItemDetailResponse)
def return_inventory_item_loan(
    item_id: int,
    loan_id: int,
    payload: LoanReturn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemDetailResponse:
    return return_loan(db, item_id, loan_id, payload, actor_id=user.id, include_sensitive=can_view_sensitive(user))


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
    return await add_item_image(
        db,
        item_id,
        file,
        is_primary=is_primary,
        actor_id=user.id,
        include_sensitive=can_view_sensitive(user),
    )


@router.get("/items/{item_id}/images/{image_id}/file")
def download_inventory_item_image(
    item_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(READ_PERMISSION)),
) -> FileResponse:
    media_file = get_item_image_file(db, item_id, image_id, include_sensitive=can_view_sensitive(user))
    return FileResponse(
        media_file.path,
        media_type=media_file.content_type,
        filename=media_file.filename,
        content_disposition_type="inline",
    )


@router.patch("/items/{item_id}/images/{image_id}", response_model=ItemImageResponse)
def update_inventory_item_image(
    item_id: int,
    image_id: int,
    payload: ItemImageUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemImageResponse:
    return update_item_image_metadata(
        db,
        item_id,
        image_id,
        payload,
        actor_id=user.id,
        include_sensitive=can_view_sensitive(user),
    )


@router.delete("/items/{item_id}/images/{image_id}", response_model=ItemDetailResponse)
def delete_inventory_item_image(
    item_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemDetailResponse:
    return archive_item_image(db, item_id, image_id, actor_id=user.id, include_sensitive=can_view_sensitive(user))


@router.post("/items/{item_id}/attachments", response_model=ItemAttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_inventory_item_attachment(
    item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemAttachmentResponse:
    return await add_item_attachment(db, item_id, file, actor_id=user.id, include_sensitive=can_view_sensitive(user))


@router.get("/items/{item_id}/attachments/{attachment_id}/download")
def download_inventory_item_attachment(
    item_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(READ_PERMISSION)),
) -> FileResponse:
    media_file = get_item_attachment_file(db, item_id, attachment_id, include_sensitive=can_view_sensitive(user))
    return FileResponse(
        media_file.path,
        media_type=media_file.content_type,
        filename=media_file.filename,
    )


@router.delete("/items/{item_id}/attachments/{attachment_id}", response_model=ItemDetailResponse)
def delete_inventory_item_attachment(
    item_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ItemDetailResponse:
    return archive_item_attachment(
        db,
        item_id,
        attachment_id,
        actor_id=user.id,
        include_sensitive=can_view_sensitive(user),
    )


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
