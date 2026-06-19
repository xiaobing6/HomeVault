# HomeVault Phase 3 Inventory Design

## Purpose

Phase 3 turns HomeVault from a configured shell into a usable household inventory system. It builds the complete item workflow on top of Phase 1 authentication/RBAC and Phase 2 core configuration.

The chosen scope is the full Phase 3 option: item creation and editing, images, attachments, tags, card and table views, search and filters, detail modal, category-driven custom fields, location and container placement, status changes, loans and returns, quantity history, and permission boundaries for administrator, editor, and viewer users.

Phase 4 remains separate. Reminder center pages, global audit log UI, deeper user/role management screens, and broader soft-delete management polish stay out of this phase.

## Confirmed UI Direction

The inventory entry point uses layout A from the visual review:

- Left side: location tree, category tree, and quick filters.
- Right side: card and table views for items.
- Top area: search, filter controls, view toggle, and add-item action.
- Item detail opens as a modal over the workbench instead of navigating away.

The detail modal keeps the user in context. It shows the item title, category, status, location or container, quantity, primary actions, images, custom fields, attachments, movements, loans, and quantity history.

Add and edit use the same step-based drawer or modal:

1. Category selection.
2. Basic information.
3. Location or container.
4. Category custom fields.
5. Images and attachments.

Changing the category while editing an existing item is allowed but guarded with a Chinese warning. Existing historical values are preserved, while the active editable fields switch to the new category definition.

## Backend Data Model

Phase 3 adds an independent inventory model layer. It references configuration tables but keeps item behavior in inventory-specific files.

### Items

`items` stores the main item record:

- Name, description, category, status, quantity, unit, privacy level.
- Owner family member and current keeper family member.
- Current location node or current container item.
- Whether the item itself can act as a container.
- Archive state and archive reason.
- Created, updated, and archived timestamps.

An item can have either `location_node_id` or `container_item_id`, never both. Exit-style statuses such as discarded, gifted, sold, lost, or consumed may have neither location nor container.

### Custom Values

`item_attribute_values` stores values for category-defined fields. Values are keyed by item and `attribute_definition_id`.

The service layer validates values using the Phase 2 field definitions:

- Required active fields must be present on create.
- Single-select and multi-select values must match active options.
- Number and money fields must parse as numeric values.
- Date and datetime fields must parse as valid dates.
- Boolean fields must be true or false.
- Attachment-style field values reference stored attachments where applicable.

Inactive field definitions are not editable by default, but historical values remain visible on detail.

### Images And Attachments

`item_images` stores image metadata and local file paths:

- Original filename, stored filename, content type, byte size.
- Sort order and primary-image flag.
- Archive state.

`item_attachments` stores non-image attachments with similar metadata.

The first active image becomes primary unless another primary image is explicitly selected. Deleting images or attachments archives metadata and removes them from normal views; physical cleanup can be handled later.

### Tags

`tags` stores reusable tag names. `item_tags` links items and tags.

Tags are created on demand during item create/edit and are searchable. Duplicate tag names are rejected case-insensitively at the service layer.

### Movement, Quantity, And Loans

`item_movements` records location, container, and status changes. It stores previous and new values plus reason, note, actor, and timestamp.

`item_quantity_changes` records every quantity adjustment:

- Quantity before and after.
- Delta.
- Unit.
- Reason and note.
- Actor and timestamp.

Quantity is never silently overwritten. Item create writes an initial quantity history record.

`item_loans` records borrowing:

- Borrower name, contact, expected return date, loan note.
- Returned timestamp, return location or container, and return note.
- Actor fields for loan and return.

An item can have at most one active unreturned loan. Returning an item chooses a location or container and creates both a loan return update and a movement/status history entry.

## Core Business Rules

Location and container placement are mutually exclusive.

Containers are ordinary items with `is_container=true`. A container may live in a location or inside another container.

Container nesting is limited to 5 levels. The service layer rejects placing an item into itself or into any descendant container. The Chinese error message is: `这个容器不能放进自己或自己的下级容器中`.

When a container moves, child items are not rewritten. Their effective location is resolved through the container chain.

Exit-style statuses may clear current location and container. Movement and status history remain.

Archiving an item is a soft delete. Archived items are hidden from default lists but can be included with an archive filter.

Important write operations run in one transaction. Partial saves are rejected and rolled back.

## API Design

All inventory routes live under `/api/items` unless noted.

Read endpoints require `items:view`.

Create and edit endpoints require `items:create` or `items:edit` as appropriate.

Archiving requires `items:archive`.

### Item Routes

- `GET /api/items`
  - Lists items with pagination.
  - Supports search, category, residence, location, status, tag, loan, archived, owner, keeper, and custom-field filters.
  - Supports card-friendly and table-friendly response fields.

- `POST /api/items`
  - Creates an item with basic fields, custom values, tags, and initial location or container.
  - Writes initial quantity history.
  - Accepts images and attachments either as follow-up upload calls or as metadata-free empty arrays.

- `GET /api/items/{id}`
  - Returns the full detail payload for the modal.
  - Includes images, attachments, tags, custom values, location/container path, recent movements, quantity history summary, and active loan.

- `PATCH /api/items/{id}`
  - Updates basic fields, custom values, owner, keeper, tags, and privacy level.
  - Does not silently adjust quantity. Quantity changes use the quantity endpoint.
  - Does not move the item. Movement uses the move endpoint.

- `POST /api/items/{id}/archive`
  - Archives the item with an optional reason.

### Placement And Status Routes

- `POST /api/items/{id}/move`
  - Moves the item to either a location node or a container item.
  - Validates mutual exclusion and container cycles.
  - Writes movement history.

- `POST /api/items/{id}/status`
  - Changes item status.
  - Exit-style statuses may clear placement.
  - Writes movement/status history.

### Quantity Routes

- `POST /api/items/{id}/quantity-adjustments`
  - Adjusts quantity by setting a new quantity or applying a delta.
  - Requires reason.
  - Writes quantity history.

- `GET /api/items/{id}/quantity-adjustments`
  - Returns quantity history newest first.

### Loan Routes

- `POST /api/items/{id}/loans`
  - Creates a loan record and changes item status to loaned when configured.
  - Requires borrower name.
  - Rejects a second active loan.

- `POST /api/items/{id}/loans/{loan_id}/return`
  - Marks a loan returned.
  - Requires a return location or return container unless the target status permits no placement.
  - Writes movement and status history.

### History And Upload Routes

- `GET /api/items/{id}/movements`
  - Returns movement and status history.

- `POST /api/items/{id}/images`
  - Uploads one image.
  - Validates image content type and size.

- `PATCH /api/items/{id}/images/{image_id}`
  - Updates primary flag or sort order.

- `DELETE /api/items/{id}/images/{image_id}`
  - Archives image metadata.

- `POST /api/items/{id}/attachments`
  - Uploads one attachment.

- `DELETE /api/items/{id}/attachments/{attachment_id}`
  - Archives attachment metadata.

- `GET /api/tags`
  - Lists tags, optionally filtered by search text.

- `POST /api/tags`
  - Creates a reusable tag.

## Frontend Design

### Inventory Workbench

`ItemsPage.vue` becomes the main inventory surface.

The left filter panel contains:

- Location tree by residence.
- Category tree.
- Quick filters for borrowed, overdue loan, container items, archived items, and items with date-like fields approaching expiry.

The right work area contains:

- Search input.
- Filter summary chips.
- Card/table view toggle.
- Sort selector.
- Add item button.
- Item card grid and table.

Cards show primary image, name, category, status, location or container, owner, quantity/unit, privacy marker, tag summary, and due/expiry marker when available.

The table view shows dense operational columns for users who want a ledger-like view.

### Detail Modal

`ItemDetailModal.vue` opens from card or table rows.

Tabs:

- Overview.
- Custom fields.
- Images and attachments.
- Movement history.
- Quantity history.
- Loan records.

Primary actions:

- Edit.
- Move.
- Change status.
- Borrow.
- Return.
- Adjust quantity.
- Archive.

The modal stays open after actions and refreshes its detail payload.

### Add/Edit Drawer

`ItemFormDrawer.vue` uses the confirmed five-step flow:

1. Category.
2. Basic information.
3. Location or container.
4. Custom fields.
5. Images and attachments.

The custom field step is generated from the selected category's active `attribute_definitions`.

The drawer validates required fields client-side for quick feedback. The backend remains authoritative and returns Chinese validation errors.

### Action Dialogs

Small focused dialogs handle:

- Moving an item.
- Changing status.
- Borrowing an item.
- Returning a loan.
- Adjusting quantity.
- Archiving an item.

These dialogs use the same permission rules as the backend and hide or disable actions the user cannot perform.

## Permissions

Administrator:

- Can create, edit, move, borrow, return, adjust quantity, upload media, manage tags, and archive items.

Editor:

- Can create and edit items.
- Can move items.
- Can borrow and return items.
- Can adjust quantity.
- Can upload images and attachments.
- Cannot access core configuration screens unless explicitly granted `config:manage`.

Viewer:

- Can list items, open detail modals, view images, attachments, custom fields, and history.
- Cannot create, edit, move, borrow, return, adjust quantity, upload, or archive.

Direct unauthorized API calls return structured Chinese errors.

## Error Handling

The frontend displays clear Chinese messages and does not expose raw error codes.

Important messages include:

- `请先登录`
- `你没有权限执行此操作`
- `物品名称不能为空`
- `请选择分类`
- `请选择位置或容器，不能同时选择两者`
- `这个容器不能放进自己或自己的下级容器中`
- `数量调整必须填写原因`
- `该物品已有未归还的借出记录`
- `上传文件类型不支持`
- `上传文件过大`

## Testing And Acceptance

Backend tests cover:

- Inventory migrations.
- Model relationships.
- Item create/edit/detail/list.
- Custom field validation.
- Search and filters.
- Location/container mutual exclusion.
- Container depth and cycle rejection.
- Move and status history.
- Quantity adjustment history.
- Loan and return lifecycle.
- Image and attachment metadata.
- Tag reuse and duplicate rejection.
- Role permission boundaries.

Frontend verification covers:

- Workbench renders with authenticated user.
- Card and table views both show items.
- Search and filters update list results.
- Add drawer follows category-first flow.
- Custom fields appear after category selection.
- Detail opens as a modal.
- Move, borrow, return, quantity adjustment, and archive actions refresh detail.
- Viewer cannot see or trigger write actions.

Browser acceptance flow:

1. Admin logs in.
2. Admin creates an item with image, attachment, tags, category fields, quantity, and location.
3. Admin searches and filters the item.
4. Admin opens detail modal.
5. Admin moves the item.
6. Admin creates a container item and places the first item inside it.
7. Admin borrows and returns the item.
8. Admin adjusts quantity.
9. Admin confirms movement, loan, and quantity histories.
10. Viewer logs in and can view the item but cannot modify it.

## Out Of Scope For Phase 3

- Standalone reminder center page.
- Global audit log UI.
- Full user and role management screens.
- External notification integrations.
- QR code workflows.
- Mobile app or mini-program screens.
- Bulk import and export.
- Physical deletion of historical item data.

## Completion Criteria

Phase 3 is complete when:

- Backend tests pass.
- Frontend build passes.
- Alembic upgrades a fresh SQLite database through the Phase 3 migration.
- Admin can complete the full item lifecycle from browser acceptance.
- Editor can perform item maintenance without configuration access.
- Viewer can browse and inspect items without write access.
- Images, attachments, tags, custom fields, movements, loans, and quantity history are visible from the detail modal.
- The default item list hides archived items but can include them through filters.
