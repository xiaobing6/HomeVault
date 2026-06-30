# HomeVault Phase 4C-4 Inventory Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe create-only CSV import workflow with template download, validation preview, row errors, and confirmed all-or-nothing import.

**Architecture:** Keep import parsing and validation in a new backend service module so `inventory.py` does not grow further. The service converts CSV rows into existing `ItemCreate` payloads, then confirmation reuses `create_item` in one transaction boundary. The frontend adds typed API/store helpers and a focused import dialog wired from the existing inventory toolbar.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, csv module, Vue 3, TypeScript, Pinia, Element Plus, Axios.

---

## File Structure

- Create `backend/app/services/inventory_import.py`: CSV template, parsing, row validation, preview cache, confirm import.
- Modify `backend/app/schemas/inventory.py`: import preview/confirm request and response schemas.
- Modify `backend/app/api/routes/inventory.py`: add `/items/import/template.csv`, `/items/import/preview`, and `/items/import/confirm` before dynamic item routes.
- Modify `backend/tests/test_inventory_api.py`: add import template, preview, confirm, and permission tests.
- Modify `frontend/src/api/inventory.ts`: add import types and API helpers.
- Modify `frontend/src/stores/inventory.ts`: add import actions and refresh after confirm.
- Modify `frontend/src/components/items/ItemToolbar.vue`: add import toolbar emit/button for users with create permission.
- Create `frontend/src/components/items/ItemImportDialog.vue`: upload, preview summary, row errors, confirm import.
- Modify `frontend/src/pages/ItemsPage.vue`: open import dialog, download template, refresh list after confirm.
- Create `frontend/tests/inventory-import-contract.mjs`: source-level import wiring checks.

## Task 1: Backend Import API Tests

**Files:**
- Modify `backend/tests/test_inventory_api.py`

- [ ] **Step 1: Add CSV helper imports and helpers**

At the top of `backend/tests/test_inventory_api.py`, extend imports:

```python
from io import BytesIO, StringIO
```

Replace the existing `from io import StringIO` import with the combined import above.

Add this helper near `create_item`:

```python
def csv_upload(content: str) -> dict[str, tuple[str, bytes, str]]:
    return {"file": ("items.csv", content.encode("utf-8"), "text/csv")}
```

- [ ] **Step 2: Write template endpoint test**

Append this test after the CSV export test:

```python
def test_inventory_import_template_includes_static_and_custom_columns(client: TestClient, db_session: Session) -> None:
    headers = login(client)
    ids = inventory_ids(db_session)
    db_session.add(
        AttributeDefinition(
            category_id=ids["category_id"],
            key="serial_number",
            name="Serial number",
            field_type="text",
            is_active=True,
        )
    )
    db_session.commit()

    response = client.get("/api/items/import/template.csv", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    header = response.text.splitlines()[0].split(",")
    assert header[:14] == [
        "name",
        "description",
        "category",
        "status",
        "quantity",
        "unit",
        "owner",
        "keeper",
        "residence",
        "location",
        "container",
        "is_container",
        "privacy_level",
        "tags",
    ]
    assert "field:serial_number" in header
```

- [ ] **Step 3: Write preview success test**

Append:

```python
def test_inventory_import_preview_validates_rows_without_creating_items(client: TestClient, db_session: Session) -> None:
    headers = login(client)
    content = "\n".join(
        [
            "name,description,category,status,quantity,unit,owner,keeper,residence,location,container,is_container,privacy_level,tags",
            "Imported folder,From CSV,documents,in_stock,3,pcs,Alex,Alex,Main residence,Shelf,,true,sensitive,\"Travel, Paper\"",
        ]
    )

    response = client.post("/api/items/import/preview", headers=headers, files=csv_upload(content))
    item_count = db_session.scalar(select(Item.id).where(Item.name == "Imported folder").limit(1))

    assert response.status_code == 200
    body = response.json()
    assert body["token"]
    assert body["total_count"] == 1
    assert body["valid_count"] == 1
    assert body["invalid_count"] == 0
    assert body["rows"][0]["row_number"] == 2
    assert body["rows"][0]["is_valid"] is True
    assert body["rows"][0]["normalized"]["name"] == "Imported folder"
    assert body["rows"][0]["normalized"]["privacy_level"] == "sensitive"
    assert body["rows"][0]["warnings"] == []
    assert item_count is None
```

- [ ] **Step 4: Write preview error test**

Append:

```python
def test_inventory_import_preview_reports_row_errors(client: TestClient) -> None:
    headers = login(client)
    content = "\n".join(
        [
            "name,description,category,status,quantity,unit,owner,keeper,residence,location,container,is_container,privacy_level,tags",
            ",Missing name,documents,in_stock,abc,pcs,Alex,Alex,Main residence,Shelf,,false,normal,",
            "Bad category,,unknown,in_stock,1,pcs,Alex,Alex,Main residence,Shelf,,false,normal,",
        ]
    )

    response = client.post("/api/items/import/preview", headers=headers, files=csv_upload(content))

    assert response.status_code == 200
    body = response.json()
    assert body["token"] is None
    assert body["total_count"] == 2
    assert body["valid_count"] == 0
    assert body["invalid_count"] == 2
    assert body["rows"][0]["is_valid"] is False
    assert {error["field"] for error in body["rows"][0]["errors"]} == {"name", "quantity"}
    assert body["rows"][1]["errors"][0]["field"] == "category"
```

- [ ] **Step 5: Write confirm test**

Append:

```python
def test_inventory_import_confirm_creates_previewed_items(client: TestClient, db_session: Session) -> None:
    headers = login(client)
    content = "\n".join(
        [
            "name,description,category,status,quantity,unit,owner,keeper,residence,location,container,is_container,privacy_level,tags",
            "Imported folder,From CSV,documents,in_stock,3,pcs,Alex,Alex,Main residence,Shelf,,true,normal,\"Travel, Paper\"",
            "Imported envelope,Second row,documents,in_stock,1,pcs,Alex,Alex,Main residence,Drawer,,false,normal,Paper",
        ]
    )
    preview = client.post("/api/items/import/preview", headers=headers, files=csv_upload(content))
    token = preview.json()["token"]

    response = client.post("/api/items/import/confirm", headers=headers, json={"token": token})
    imported_items = db_session.scalars(select(Item).where(Item.name.like("Imported%")).order_by(Item.name)).all()

    assert response.status_code == 200
    assert response.json()["imported_count"] == 2
    assert len(response.json()["item_ids"]) == 2
    assert [item.name for item in imported_items] == ["Imported envelope", "Imported folder"]
    assert imported_items[1].quantity == 3
    assert imported_items[1].is_container is True
    assert imported_items[1].tag_links[0].tag.normalized_name == "paper"
```

- [ ] **Step 6: Write invalid token and permission tests**

Append:

```python
def test_inventory_import_confirm_rejects_invalid_token(client: TestClient) -> None:
    headers = login(client)

    response = client.post("/api/items/import/confirm", headers=headers, json={"token": "missing-token"})

    assert response.status_code == 400
    assert response.json()["message"]


def test_inventory_import_requires_create_permission(client: TestClient) -> None:
    viewer_headers = login(client, "viewer", "Viewer123!")
    content = "\n".join(
        [
            "name,description,category,status,quantity,unit,owner,keeper,residence,location,container,is_container,privacy_level,tags",
            "Imported folder,From CSV,documents,in_stock,1,pcs,Alex,Alex,Main residence,Shelf,,false,normal,",
        ]
    )

    template = client.get("/api/items/import/template.csv", headers=viewer_headers)
    preview = client.post("/api/items/import/preview", headers=viewer_headers, files=csv_upload(content))
    confirm = client.post("/api/items/import/confirm", headers=viewer_headers, json={"token": "any"})

    assert template.status_code == 403
    assert preview.status_code == 403
    assert confirm.status_code == 403
```

- [ ] **Step 7: Run tests and verify they fail**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_api.py::test_inventory_import_template_includes_static_and_custom_columns tests/test_inventory_api.py::test_inventory_import_preview_validates_rows_without_creating_items tests/test_inventory_api.py::test_inventory_import_preview_reports_row_errors tests/test_inventory_api.py::test_inventory_import_confirm_creates_previewed_items tests/test_inventory_api.py::test_inventory_import_confirm_rejects_invalid_token tests/test_inventory_api.py::test_inventory_import_requires_create_permission -q
```

Expected: failures with 404/405 because import endpoints do not exist yet.

## Task 2: Backend Import Schemas And Service

**Files:**
- Modify `backend/app/schemas/inventory.py`
- Create `backend/app/services/inventory_import.py`

- [ ] **Step 1: Add import response schemas**

In `backend/app/schemas/inventory.py`, after `ItemExportRequest`, add:

```python
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
```

- [ ] **Step 2: Create import service module**

Create `backend/app/services/inventory_import.py` with:

```python
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from io import StringIO
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import bad_request
from app.models.configuration import AttributeDefinition, Category, FamilyMember, ItemStatus, LocationNode
from app.models.inventory import Item
from app.schemas.inventory import (
    ImportConfirmResponse,
    ImportFieldMessage,
    ImportPreviewResponse,
    ImportRowPreview,
    ItemAttributeValueInput,
    ItemCreate,
)
from app.services.inventory import create_item, validate_basic_placement
from app.services.privacy import normalize_privacy_level

STATIC_IMPORT_COLUMNS = [
    "name",
    "description",
    "category",
    "status",
    "quantity",
    "unit",
    "owner",
    "keeper",
    "residence",
    "location",
    "container",
    "is_container",
    "privacy_level",
    "tags",
]
MAX_IMPORT_ROWS = 500
IMPORT_TOKEN_TTL = timedelta(minutes=30)
TRUE_VALUES = {"1", "true", "yes", "y", "是", "真"}
FALSE_VALUES = {"0", "false", "no", "n", "否", "假", ""}


@dataclass
class ImportCacheEntry:
    expires_at: datetime
    payloads: list[ItemCreate]


IMPORT_PREVIEW_CACHE: dict[str, ImportCacheEntry] = {}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def cleanup_import_cache() -> None:
    now = utcnow()
    expired_tokens = [token for token, entry in IMPORT_PREVIEW_CACHE.items() if entry.expires_at <= now]
    for token in expired_tokens:
        IMPORT_PREVIEW_CACHE.pop(token, None)
```

- [ ] **Step 3: Add template generation**

Append to `inventory_import.py`:

```python
def import_template_csv(db: Session) -> str:
    definitions = db.scalars(
        select(AttributeDefinition)
        .where(AttributeDefinition.is_active.is_(True))
        .order_by(AttributeDefinition.sort_order, AttributeDefinition.id)
    ).all()
    columns = [*STATIC_IMPORT_COLUMNS]
    for definition in definitions:
        column = f"field:{definition.key}"
        if column not in columns:
            columns.append(column)

    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(columns)
    return output.getvalue()
```

- [ ] **Step 4: Add parsing helpers**

Append:

```python
def normalize_cell(value: object) -> str:
    return str(value or "").strip()


def parse_bool(value: str, field: str, errors: list[ImportFieldMessage]) -> bool:
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    errors.append(ImportFieldMessage(field=field, message="请输入是或否"))
    return False


def parse_quantity(value: str, errors: list[ImportFieldMessage]) -> Decimal:
    if value == "":
        return Decimal("1")
    try:
        return Decimal(value)
    except InvalidOperation:
        errors.append(ImportFieldMessage(field="quantity", message="数量格式不正确"))
        return Decimal("1")


def split_tags(value: str) -> list[str]:
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def read_import_csv(content: bytes) -> list[tuple[int, dict[str, str]]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None:
        raise bad_request("CSV 文件为空")

    rows: list[tuple[int, dict[str, str]]] = []
    for index, row in enumerate(reader, start=2):
        normalized_row = {str(key or "").strip(): normalize_cell(value) for key, value in row.items()}
        if any(value != "" for value in normalized_row.values()):
            rows.append((index, normalized_row))
    if not rows:
        raise bad_request("CSV 文件没有可导入的数据")
    if len(rows) > MAX_IMPORT_ROWS:
        raise bad_request("一次最多导入 500 行")
    return rows
```

- [ ] **Step 5: Add lookup helpers**

Append:

```python
def one_by_code_or_name(rows: list[object], value: str, field: str, errors: list[ImportFieldMessage]):
    if value == "":
        errors.append(ImportFieldMessage(field=field, message="不能为空"))
        return None
    matches = [
        row for row in rows
        if getattr(row, "code", None) == value or getattr(row, "name", None) == value
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        errors.append(ImportFieldMessage(field=field, message="匹配到多条记录，请使用唯一值"))
        return None
    errors.append(ImportFieldMessage(field=field, message="不存在或未启用"))
    return None


def optional_member(rows: list[FamilyMember], value: str, field: str, errors: list[ImportFieldMessage]) -> int | None:
    if value == "":
        return None
    matches = [member for member in rows if member.name == value]
    if len(matches) == 1:
        return matches[0].id
    if len(matches) > 1:
        errors.append(ImportFieldMessage(field=field, message="家庭成员名称不唯一"))
        return None
    errors.append(ImportFieldMessage(field=field, message="家庭成员不存在"))
    return None
```

- [ ] **Step 6: Add placement and custom field helpers**

Append:

```python
def location_path(node: LocationNode) -> str:
    names = [node.name]
    parent = node.parent
    while parent is not None:
        names.append(parent.name)
        parent = parent.parent
    return " / ".join(reversed(names))


def optional_location(
    locations: list[LocationNode],
    value: str,
    residence: str,
    errors: list[ImportFieldMessage],
) -> int | None:
    if value == "":
        return None
    matches = [
        node for node in locations
        if node.name == value or location_path(node) == value
    ]
    if residence:
        matches = [node for node in matches if node.residence is not None and node.residence.name == residence]
    if len(matches) == 1:
        return matches[0].id
    if len(matches) > 1:
        errors.append(ImportFieldMessage(field="location", message="位置名称不唯一，请填写 residence 或完整路径"))
        return None
    errors.append(ImportFieldMessage(field="location", message="位置不存在"))
    return None


def optional_container(containers: list[Item], value: str, errors: list[ImportFieldMessage]) -> int | None:
    if value == "":
        return None
    matches = [item for item in containers if item.name == value]
    if len(matches) == 1:
        return matches[0].id
    if len(matches) > 1:
        errors.append(ImportFieldMessage(field="container", message="容器名称不唯一"))
        return None
    errors.append(ImportFieldMessage(field="container", message="容器不存在"))
    return None


def build_attribute_values(
    row: dict[str, str],
    definitions: list[AttributeDefinition],
    category_id: int,
) -> list[ItemAttributeValueInput]:
    values: list[ItemAttributeValueInput] = []
    for definition in definitions:
        if definition.category_id != category_id or not definition.is_active:
            continue
        column = f"field:{definition.key}"
        if column in row:
            values.append(ItemAttributeValueInput(attribute_definition_id=definition.id, value=row[column]))
    return values
```

- [ ] **Step 7: Add preview validation**

Append:

```python
def build_import_context(db: Session):
    return {
        "categories": db.scalars(select(Category).where(Category.is_active.is_(True))).all(),
        "statuses": db.scalars(select(ItemStatus).where(ItemStatus.is_active.is_(True))).all(),
        "members": db.scalars(select(FamilyMember).where(FamilyMember.is_active.is_(True))).all(),
        "locations": db.scalars(select(LocationNode).where(LocationNode.is_active.is_(True))).all(),
        "containers": db.scalars(
            select(Item).where(Item.is_container.is_(True), Item.is_archived.is_(False))
        ).all(),
        "definitions": db.scalars(select(AttributeDefinition).where(AttributeDefinition.is_active.is_(True))).all(),
    }


def validate_import_row(db: Session, row_number: int, row: dict[str, str], context) -> tuple[ImportRowPreview, ItemCreate | None]:
    errors: list[ImportFieldMessage] = []
    warnings: list[ImportFieldMessage] = []
    name = row.get("name", "").strip()
    if name == "":
        errors.append(ImportFieldMessage(field="name", message="名称不能为空"))

    category = one_by_code_or_name(context["categories"], row.get("category", ""), "category", errors)
    status = one_by_code_or_name(context["statuses"], row.get("status", ""), "status", errors)
    quantity = parse_quantity(row.get("quantity", ""), errors)
    owner_id = optional_member(context["members"], row.get("owner", ""), "owner", errors)
    keeper_id = optional_member(context["members"], row.get("keeper", ""), "keeper", errors)
    location_id = optional_location(
        context["locations"],
        row.get("location", ""),
        row.get("residence", ""),
        errors,
    )
    container_id = optional_container(context["containers"], row.get("container", ""), errors)
    is_container = parse_bool(row.get("is_container", ""), "is_container", errors)
    privacy_level = normalize_privacy_level(row.get("privacy_level", "") or "normal")

    if category is not None and name:
        existing = db.scalar(
            select(Item.id)
            .where(Item.name == name, Item.category_id == category.id, Item.is_archived.is_(False))
            .limit(1)
        )
        if existing is not None:
            warnings.append(ImportFieldMessage(field="name", message="同分类下已有同名物品"))

    payload: ItemCreate | None = None
    if category is not None and status is not None and not errors:
        try:
            validate_basic_placement(db, status, location_id, container_id)
        except Exception:
            errors.append(ImportFieldMessage(field="location", message="位置或容器不符合当前状态"))

    if category is not None and status is not None and not errors:
        payload = ItemCreate(
            name=name,
            description=row.get("description", ""),
            category_id=category.id,
            status_id=status.id,
            quantity=quantity,
            unit=row.get("unit", "") or "件",
            owner_member_id=owner_id,
            keeper_member_id=keeper_id,
            location_node_id=location_id,
            container_item_id=container_id,
            is_container=is_container,
            privacy_level=privacy_level,
            attribute_values=build_attribute_values(row, context["definitions"], category.id),
            tags=split_tags(row.get("tags", "")),
        )

    normalized = payload.model_dump(mode="json") if payload is not None else None
    return (
        ImportRowPreview(
            row_number=row_number,
            original=row,
            normalized=normalized,
            errors=errors,
            warnings=warnings,
            is_valid=payload is not None and not errors,
        ),
        payload,
    )
```

- [ ] **Step 8: Add preview and confirm service functions**

Append:

```python
def preview_inventory_import(db: Session, content: bytes) -> ImportPreviewResponse:
    cleanup_import_cache()
    rows = read_import_csv(content)
    context = build_import_context(db)
    previews: list[ImportRowPreview] = []
    payloads: list[ItemCreate] = []
    for row_number, row in rows:
        preview, payload = validate_import_row(db, row_number, row, context)
        previews.append(preview)
        if payload is not None and preview.is_valid:
            payloads.append(payload)

    invalid_count = sum(1 for row in previews if not row.is_valid)
    token = None
    if invalid_count == 0:
        token = token_urlsafe(32)
        IMPORT_PREVIEW_CACHE[token] = ImportCacheEntry(
            expires_at=utcnow() + IMPORT_TOKEN_TTL,
            payloads=payloads,
        )
    return ImportPreviewResponse(
        token=token,
        rows=previews,
        total_count=len(previews),
        valid_count=len(previews) - invalid_count,
        invalid_count=invalid_count,
    )


def confirm_inventory_import(db: Session, token: str, actor_id: int | None = None) -> ImportConfirmResponse:
    cleanup_import_cache()
    entry = IMPORT_PREVIEW_CACHE.pop(token, None)
    if entry is None or entry.expires_at <= utcnow():
        raise bad_request("导入预览已过期，请重新上传")

    item_ids: list[int] = []
    try:
        with db.begin_nested():
            for payload in entry.payloads:
                detail = create_item(db, payload, actor_id=actor_id)
                item_ids.append(detail.id)
    except Exception:
        raise
    return ImportConfirmResponse(imported_count=len(item_ids), item_ids=item_ids)
```

- [ ] **Step 9: Run backend tests and record failures**

Run the same command from Task 1 Step 7.

Expected: routes still missing, schemas and service import cleanly.

## Task 3: Backend Routes

**Files:**
- Modify `backend/app/api/routes/inventory.py`

- [ ] **Step 1: Add imports**

In `backend/app/api/routes/inventory.py`, add `Response` already exists from 4C-3 and add schema imports:

```python
    ImportConfirmRequest,
    ImportConfirmResponse,
    ImportPreviewResponse,
```

Add service imports:

```python
from app.services.inventory_import import (
    confirm_inventory_import,
    import_template_csv,
    preview_inventory_import,
)
```

- [ ] **Step 2: Add routes before `/items/{item_id}`**

Insert after `/items/export.csv`:

```python
@router.get("/items/import/template.csv")
def inventory_import_template(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(CREATE_PERMISSION)),
) -> Response:
    return Response(
        content=import_template_csv(db),
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": 'attachment; filename="homevault-import-template.csv"',
        },
    )


@router.post("/items/import/preview", response_model=ImportPreviewResponse)
async def preview_inventory_items_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(CREATE_PERMISSION)),
) -> ImportPreviewResponse:
    return preview_inventory_import(db, await file.read())


@router.post("/items/import/confirm", response_model=ImportConfirmResponse)
def confirm_inventory_items_import(
    payload: ImportConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(CREATE_PERMISSION)),
) -> ImportConfirmResponse:
    return confirm_inventory_import(db, payload.token, actor_id=user.id)
```

- [ ] **Step 3: Run targeted backend tests**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_api.py::test_inventory_import_template_includes_static_and_custom_columns tests/test_inventory_api.py::test_inventory_import_preview_validates_rows_without_creating_items tests/test_inventory_api.py::test_inventory_import_preview_reports_row_errors tests/test_inventory_api.py::test_inventory_import_confirm_creates_previewed_items tests/test_inventory_api.py::test_inventory_import_confirm_rejects_invalid_token tests/test_inventory_api.py::test_inventory_import_requires_create_permission -q
```

Expected: all six tests pass. If validation message details differ but behavior is correct, adjust tests only to keep assertions behavior-level.

- [ ] **Step 4: Run inventory API tests**

Run:

```powershell
python -m pytest tests/test_inventory_api.py -q
```

Expected: all inventory API tests pass.

## Task 4: Frontend Import Contracts

**Files:**
- Create `frontend/tests/inventory-import-contract.mjs`

- [ ] **Step 1: Add failing contract test**

Create `frontend/tests/inventory-import-contract.mjs`:

```js
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
assert.match(api, /\\/items\\/import\\/template\\.csv/)
assert.match(api, /\\/items\\/import\\/preview/)
assert.match(api, /\\/items\\/import\\/confirm/)

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
```

- [ ] **Step 2: Run contract and verify failure**

Run from `frontend`:

```powershell
node .\tests\inventory-import-contract.mjs
```

Expected: failure because import API, store actions, toolbar emit, page wiring, and dialog do not exist yet.

## Task 5: Frontend API And Store

**Files:**
- Modify `frontend/src/api/inventory.ts`
- Modify `frontend/src/stores/inventory.ts`

- [ ] **Step 1: Add import types and API helpers**

In `frontend/src/api/inventory.ts`, after `ItemExportRequest`, add:

```ts
export interface ImportFieldMessage {
  field: string
  message: string
}

export interface ImportRowPreview {
  row_number: number
  original: Record<string, string>
  normalized: Record<string, unknown> | null
  errors: ImportFieldMessage[]
  warnings: ImportFieldMessage[]
  is_valid: boolean
}

export interface ImportPreviewResponse {
  token: string | null
  rows: ImportRowPreview[]
  total_count: number
  valid_count: number
  invalid_count: number
}

export interface ImportConfirmRequest {
  token: string
}

export interface ImportConfirmResponse {
  imported_count: number
  item_ids: number[]
}
```

After `exportItemsCsvApi`, add:

```ts
export async function downloadImportTemplateApi(): Promise<Blob> {
  const response = await apiClient.get<Blob>('/items/import/template.csv', {
    responseType: 'blob'
  })
  return response.data
}

export async function previewInventoryImportApi(file: File): Promise<ImportPreviewResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.post<ImportPreviewResponse>('/items/import/preview', formData)
  return response.data
}

export async function confirmInventoryImportApi(
  payload: ImportConfirmRequest
): Promise<ImportConfirmResponse> {
  const response = await apiClient.post<ImportConfirmResponse>('/items/import/confirm', payload)
  return response.data
}
```

- [ ] **Step 2: Add store actions**

In `frontend/src/stores/inventory.ts`, import the helpers and types:

```ts
  confirmInventoryImportApi,
  downloadImportTemplateApi,
  previewInventoryImportApi,
  type ImportConfirmRequest,
```

Add actions after `exportItemsCsv`:

```ts
async downloadImportTemplate() {
  return await downloadImportTemplateApi()
},
async previewInventoryImport(file: File) {
  return await previewInventoryImportApi(file)
},
async confirmInventoryImport(payload: ImportConfirmRequest) {
  const response = await confirmInventoryImportApi(payload)
  await this.loadItems()
  return response
},
```

- [ ] **Step 3: Run type check**

Run from `frontend`:

```powershell
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: passes after API/store wiring.

## Task 6: Frontend Import UI

**Files:**
- Modify `frontend/src/components/items/ItemToolbar.vue`
- Create `frontend/src/components/items/ItemImportDialog.vue`
- Modify `frontend/src/pages/ItemsPage.vue`

- [ ] **Step 1: Add toolbar import action**

In `ItemToolbar.vue`, import `Upload`:

```ts
import { Download, Grid, List, Operation, Plus, Search, Upload } from '@element-plus/icons-vue'
```

Add emit:

```ts
'import-items': []
```

Add this button before the create button:

```vue
<el-button v-if="canCreate" :icon="Upload" @click="emit('import-items')">
  导入
</el-button>
```

- [ ] **Step 2: Create import dialog component**

Create `frontend/src/components/items/ItemImportDialog.vue`:

```vue
<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, type UploadInstance, type UploadRawFile } from 'element-plus'
import { Check, Close, Download, Upload } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../../api/client'
import type { ImportPreviewResponse } from '../../api/inventory'
import { useInventoryStore } from '../../stores/inventory'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  imported: []
  'download-template': []
}>()

const inventory = useInventoryStore()
const uploadRef = ref<UploadInstance>()
const preview = ref<ImportPreviewResponse | null>(null)
const previewing = ref(false)
const confirming = ref(false)

const canConfirm = computed(() =>
  preview.value != null &&
  preview.value.token != null &&
  preview.value.total_count > 0 &&
  preview.value.invalid_count === 0
)

function updateOpen(open: boolean) {
  emit('update:modelValue', open)
  if (!open) reset()
}

function reset() {
  preview.value = null
  uploadRef.value?.clearFiles()
}

async function previewFile(rawFile: UploadRawFile) {
  previewing.value = true
  try {
    preview.value = await inventory.previewInventoryImport(rawFile)
    if (preview.value.invalid_count > 0) {
      ElMessage.warning('导入文件存在错误，请修正后重新上传')
    } else {
      ElMessage.success('预校验通过')
    }
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    previewing.value = false
  }
}

async function confirmImport() {
  if (!preview.value?.token) return
  confirming.value = true
  try {
    const result = await inventory.confirmInventoryImport({ token: preview.value.token })
    ElMessage.success(`已导入 ${result.imported_count} 个物品`)
    emit('imported')
    updateOpen(false)
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    confirming.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="导入物品"
    width="min(760px, 96vw)"
    destroy-on-close
    @update:model-value="updateOpen"
  >
    <div class="import-dialog">
      <div class="import-actions">
        <el-button :icon="Download" @click="emit('download-template')">下载模板</el-button>
        <el-upload
          ref="uploadRef"
          accept=".csv,text/csv"
          :auto-upload="false"
          :show-file-list="false"
          :on-change="(file) => file.raw && previewFile(file.raw)"
        >
          <el-button type="primary" :icon="Upload" :loading="previewing">上传 CSV</el-button>
        </el-upload>
      </div>

      <el-alert
        v-if="preview"
        :type="preview.invalid_count > 0 ? 'warning' : 'success'"
        :closable="false"
        show-icon
      >
        <template #title>
          共 {{ preview.total_count }} 行，{{ preview.valid_count }} 行可导入，{{ preview.invalid_count }} 行有错误
        </template>
      </el-alert>

      <el-table v-if="preview" :data="preview.rows" size="small" max-height="360" border>
        <el-table-column prop="row_number" label="行号" width="72" />
        <el-table-column label="名称" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.original.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="96">
          <template #default="{ row }">
            <el-tag :type="row.is_valid ? 'success' : 'danger'" size="small">
              {{ row.is_valid ? '可导入' : '有错误' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="错误" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.errors.map((error) => `${error.field}: ${error.message}`).join('；') || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="提醒" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.warnings.map((warning) => `${warning.field}: ${warning.message}`).join('；') || '-' }}
          </template>
        </el-table-column>
      </el-table>
    </div>

    <template #footer>
      <el-button :icon="Close" @click="updateOpen(false)">取消</el-button>
      <el-button type="primary" :icon="Check" :disabled="!canConfirm" :loading="confirming" @click="confirmImport">
        确认导入
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.import-dialog {
  display: grid;
  gap: 14px;
}

.import-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
</style>
```

- [ ] **Step 3: Wire dialog into ItemsPage**

In `frontend/src/pages/ItemsPage.vue`, import:

```ts
import ItemImportDialog from '../components/items/ItemImportDialog.vue'
```

Add state:

```ts
const importDialogOpen = ref(false)
```

Add helpers near CSV download helpers:

```ts
function downloadImportTemplateBlob(blob: Blob) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `homevault-import-template-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

async function downloadImportTemplate() {
  try {
    const blob = await inventory.downloadImportTemplate()
    downloadImportTemplateBlob(blob)
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function handleImportDone() {
  await inventory.loadItems()
}
```

Wire toolbar:

```vue
@import-items="importDialogOpen = true"
```

Render dialog near `BulkActionDialogs`:

```vue
<ItemImportDialog
  v-model="importDialogOpen"
  @download-template="downloadImportTemplate"
  @imported="handleImportDone"
/>
```

- [ ] **Step 4: Run frontend contract and type checks**

Run from `frontend`:

```powershell
node .\tests\inventory-import-contract.mjs
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: both pass.

## Task 7: Final Verification

**Files:**
- All files changed in Tasks 1-6

- [ ] **Step 1: Run backend inventory tests**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_api.py -q
```

Expected: all inventory API tests pass.

- [ ] **Step 2: Run full backend tests**

Run:

```powershell
python -m pytest -q
```

Expected: all backend tests pass.

- [ ] **Step 3: Run frontend contracts**

Run from `frontend`:

```powershell
Get-ChildItem -Path .\tests -Filter *.mjs | ForEach-Object { node $_.FullName }
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: all source contracts and type contracts pass.

- [ ] **Step 4: Run frontend build**

Run:

```powershell
npm.cmd run build
```

Expected: build exits 0. Existing VueUse pure annotation and large chunk warnings may remain.

- [ ] **Step 5: Run diff check and inspect status**

Run from repository root:

```powershell
git diff --check
git status --short --branch
```

Expected: `git diff --check` exits 0 with only CRLF warnings if present. `git status` shows only Phase 4C-4 import files.

- [ ] **Step 6: Commit implementation**

Run from repository root:

```powershell
git add backend/app/schemas/inventory.py backend/app/api/routes/inventory.py backend/app/services/inventory_import.py backend/tests/test_inventory_api.py frontend/src/api/inventory.ts frontend/src/stores/inventory.ts frontend/src/components/items/ItemToolbar.vue frontend/src/components/items/ItemImportDialog.vue frontend/src/pages/ItemsPage.vue frontend/tests/inventory-import-contract.mjs
git commit -m "feat: add inventory csv import workflow"
```

Expected: commit succeeds with only Phase 4C-4 implementation files.

## Self-Review

- Spec coverage: template, preview, row errors, confirm import, create-only scope, permissions, row limit, duplicate warnings, frontend dialog, and regression checks are each mapped to tasks.
- Placeholder scan: no placeholder task remains.
- Type consistency: backend schema names, frontend API names, store action names, and contract test regexes use the same identifiers.
