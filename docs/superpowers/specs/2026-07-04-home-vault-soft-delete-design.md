# HomeVault Soft Delete Design

## Purpose

HomeVault currently supports creating core entities, but deletion is uneven: items can be archived, configuration entities can be deactivated, and media files use archive-style delete endpoints. This feature adds a consistent soft-delete layer so created user-owned records can be removed from normal workflows without destroying history.

The first slice covers the entities most directly tied to household inventory operations:

- residences;
- location nodes;
- family members;
- items.

## Scope

This feature includes:

- database fields that mark records as deleted;
- backend delete APIs for residences, location nodes, family members, items, and bulk item deletion;
- default filtering so deleted records disappear from normal lists, bootstrap data, item search, item export, and selectable dropdowns;
- reference guards that block unsafe deletes when active inventory would be orphaned or made confusing;
- audit logs for delete actions;
- frontend delete controls with confirmation prompts on the existing management and item pages;
- backend and frontend contract tests for the new API shape and UI affordances.

This feature does not include:

- physical hard delete;
- a recovery or recycle-bin UI;
- deleting user accounts, roles, permissions, reminders, categories, custom fields, field options, item statuses, dictionary groups, or dictionary options;
- removing uploaded media files from disk when a parent record is soft-deleted;
- changing permission codes.

The other entities are intentionally outside this slice. Categories, fields, statuses, and dictionaries already have active-state management, and deleting them has broader schema/history implications. Reminders already have archive behavior. Users and roles have lockout/security rules, so they should remain separate.

## Data Model

Add soft-delete fields to these tables:

- `residences`
- `location_nodes`
- `family_members`
- `items`

Each table gets:

- `is_deleted`: boolean, default false, indexed;
- `deleted_at`: nullable timezone datetime;
- `deleted_by_id`: nullable foreign key to `users.id` with `SET NULL`.

Items also get:

- `delete_reason`: string, default empty.

The model keeps existing `is_active` and `is_archived` semantics:

- `is_active` means a configuration record is usable/selectable.
- `is_archived` means an item is removed from the active inventory lifecycle but may still be listed with `include_archived`.
- `is_deleted` means a user intentionally removed the record from normal workflows.

For item list behavior, `is_deleted` is always excluded by default. `include_archived=true` still only controls archived items, not deleted items.

## Backend Behavior

### Residence Delete

`DELETE /api/config/residences/{residence_id}` soft-deletes a residence.

The service rejects deletion when the residence has any non-deleted, non-archived item whose effective location belongs to the residence. This includes items inside containers located in that residence.

When deletion succeeds:

- `Residence.is_deleted` becomes true;
- `Residence.deleted_at` and `Residence.deleted_by_id` are set;
- all location nodes under the residence are soft-deleted too;
- `config.residence.delete` is written to audit logs.

Deleted residences do not appear in `/config/bootstrap`, `/config/residences`, residence filters, item forms, import matching, or exports. A recycle-bin feature would need explicit include-deleted APIs.

### Location Delete

`DELETE /api/config/location-nodes/{node_id}` soft-deletes a location node and its descendants.

The service rejects deletion when the node subtree has any non-deleted, non-archived item whose effective location is inside that subtree. This includes container children whose effective location resolves through a parent container.

When deletion succeeds:

- every node in the subtree gets `is_deleted=true`;
- `deleted_at` and `deleted_by_id` are set;
- `config.location.delete` is written to audit logs with the deleted subtree count.

Deleted nodes do not appear in location trees, movement forms, return forms, item create/edit forms, or location filters.

### Family Member Delete

`DELETE /api/config/family-members/{member_id}` soft-deletes a family member.

Deletion is allowed even if existing items reference the member. Historical item rows keep their `owner_member_id` and `keeper_member_id`, and item response labels can still resolve the deleted member name through the relationship. New item create/edit validation treats deleted members as unavailable.

When deletion succeeds:

- `FamilyMember.is_deleted` becomes true;
- `deleted_at` and `deleted_by_id` are set;
- `config.family_member.delete` is written to audit logs.

Deleted family members do not appear in family-member management lists, item forms, filters, import matching, or bootstrap data.

### Item Delete

`DELETE /api/items/{item_id}` soft-deletes an item.

`POST /api/items/bulk/delete` soft-deletes a deduplicated list of item IDs.

The service rejects item deletion when:

- the item has a non-deleted, non-archived child item in its container tree;
- the item has an active loan.

When deletion succeeds:

- `Item.is_deleted` becomes true;
- `deleted_at`, `deleted_by_id`, and `delete_reason` are set;
- active reminder links remain in history, but normal item lists no longer show the item;
- `inventory.item.delete` or `inventory.item.bulk_delete` is written to audit logs.

Deleted items do not appear in item lists, exports, container options, detail lookup, movement history lookup, quantity history lookup, media download endpoints, reminder item pickers, or import/export flows. A recycle-bin feature would need explicit include-deleted detail paths instead of widening existing read endpoints.

## API Shape

Configuration delete endpoints return the deleted entity response with `is_deleted=true`.

Item delete endpoint returns `ItemDetailResponse` with `is_deleted=true`.

Bulk item delete returns the existing `BulkItemOperationResponse` shape:

```json
{
  "updated_count": 2,
  "item_ids": [1, 2]
}
```

Add response fields:

- `ResidenceResponse.is_deleted`
- `LocationNodeResponse.is_deleted`
- `FamilyMemberResponse.is_deleted`
- `ItemSummaryResponse.is_deleted`
- `ItemDetailResponse.deleted_at`
- `ItemDetailResponse.delete_reason`

Configuration responses do not need `deleted_at` for normal bootstrap views.

## Frontend Behavior

### Residence and Location Panel

Residence detail gets a danger delete button near the edit button. Location detail gets the same. Both use `ElMessageBox.confirm` and explain that normal lists will hide the record after deletion.

After a successful delete:

- the detail view closes;
- configuration bootstrap reloads;
- a success message is shown.

The list views do not render deleted records because the bootstrap API already filters them out.

### Family Member Panel

The family member table adds a delete action next to edit. It uses a confirmation prompt. After deletion, the configuration store reloads and the row disappears.

### Item Page

Item detail gets a danger delete button when the user has `items:archive` and the item is not already deleted. The existing archive action remains because archive and delete are separate states.

The bulk action dropdown adds a bulk delete action guarded by `items:archive`. A confirmation dialog collects an optional reason, similar to archive.

After a successful item delete:

- the detail modal closes for single delete;
- the item list refreshes;
- selected rows are cleared after bulk delete.

## Validation and Errors

Use concise Chinese API error messages matching the existing style:

- residence with active items: "住宅下还有未删除物品，请先移动、归档或删除物品"
- location subtree with active items: "位置下还有未删除物品，请先移动、归档或删除物品"
- item with children: "请先移动、归档或删除子物品"
- item with active loan: "物品存在未归还借用记录，不能删除"
- already deleted or missing: "资源不存在"

Repeated delete requests against an already-deleted entity should behave like not found for normal endpoints.

## Testing

Backend tests:

- migrations add fields with safe defaults;
- list/bootstrap endpoints hide deleted residences, location nodes, family members, and items;
- delete APIs require existing permissions;
- residence and location deletes are blocked by active inventory;
- location delete cascades to descendants when safe;
- family member delete hides the member from config/bootstrap but preserves existing item labels;
- item delete hides items from default list, include-archived list, export, container options, and detail lookup;
- item delete is blocked by child items and active loans;
- bulk item delete deduplicates IDs and hides deleted rows;
- audit logs are written for each delete path.

Frontend tests:

- API contracts include delete helpers and `is_deleted` fields;
- configuration store exposes delete actions;
- inventory store exposes single and bulk delete actions;
- residence/location detail surfaces delete controls;
- family member table surfaces delete control;
- item detail and bulk toolbar surface delete controls guarded by archive permission.

Manual verification:

- delete a family member and confirm item history labels remain readable;
- attempt to delete a location containing items and confirm the guard message;
- delete a standalone item and confirm it disappears from lists and cannot be opened by direct URL;
- run backend pytest for configuration and inventory;
- run frontend contract/build checks.

## Rollout

The migration is additive and defaults all existing records to not deleted. No existing data should disappear after migration.

Because the first release has no recycle-bin UI, delete confirmations must be explicit. The data remains in the database, but users should experience delete as removal from normal workflows.
