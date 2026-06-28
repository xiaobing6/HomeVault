# HomeVault Phase 4C-2 Configuration Management Polish Design

Phase 4C-2 closes the largest remaining management gap in the core configuration area. Phase 2 created the configuration data model and create-first admin screens. Phase 4C-1 added residence editing to support active-only residence-name uniqueness. This slice extends that same maintenance pattern to the rest of the configuration entities that already have backend update APIs.

## Goals

- Let administrators edit and activate/deactivate existing location nodes, family members, categories, attribute definitions, attribute options, and item statuses from the core configuration UI.
- Add typed frontend API helpers and Pinia store actions for the existing backend configuration update endpoints.
- Keep the UI operational and dense, matching the current Element Plus admin panels.
- Preserve the existing backend validation rules for parent cycles, missing records, uniqueness, and permission checks.
- Add frontend contracts and focused runtime/source checks so these management controls do not silently regress.

## Non-Goals

- No custom role creation or permission editing.
- No import/export or bulk operations.
- No new dictionary group or dictionary option update endpoints. The backend currently supports dictionary create and read only, so dictionary update remains a later slice.
- No delete endpoints. Deactivation through `is_active` remains the management pattern.
- No inventory item migration or cleanup when a referenced configuration record is deactivated.

## Current State

The backend already exposes PATCH routes for:

- `/api/config/location-nodes/{node_id}`
- `/api/config/family-members/{member_id}`
- `/api/config/categories/{category_id}`
- `/api/config/attribute-definitions/{definition_id}`
- `/api/config/attribute-options/{option_id}`
- `/api/config/item-statuses/{status_id}`

The frontend only exposes `updateResidenceApi` and `configuration.updateResidence`. The configuration panels can create most records, but only residences can be edited after creation. Dictionary data is displayed read-only, matching the original Phase 2 limitation.

## Architecture

Phase 4C-2 stays frontend-first because the backend contract already exists and is covered by backend tests. The frontend configuration API module will add update payload types and one helper per existing PATCH endpoint. The Pinia configuration store will add matching actions that call the helper and reload the bootstrap payload after a successful mutation.

Each panel keeps ownership of its own form state:

- `ResidenceLocationPanel.vue` keeps residence editing and adds location-node editing.
- `FamilyMemberPanel.vue` adds member editing.
- `CategoryFieldPanel.vue` adds category editing, attribute definition editing, and attribute option create/edit controls for select-style fields.
- `DictionaryPanel.vue` adds item-status create/edit controls while keeping dictionary groups/options read-only.

This avoids a new generic editor abstraction while the panels still have different field sets and parent-option rules.

## User Experience

Administrators continue to work from `/admin/config`.

Rows that can be maintained gain an edit action with the existing Edit icon. Editing opens an Element Plus dialog with the record fields, sort order where applicable, and an active switch. Saving trims text fields, calls the store action, reloads configuration data, closes the dialog, and shows the existing Chinese success/error messages.

Location and category edit dialogs include parent selectors. The edited record itself and its descendants are excluded from parent choices in the UI where possible, while backend cycle validation remains authoritative.

Attribute options are managed inside the selected category's fields area. For `single_select` and `multi_select` definitions, admins can add options and edit option labels, sort order, and active state. Option values remain immutable after creation, matching the backend update schema.

Item statuses move from read-only display to a compact create/edit workflow. Existing system statuses can be renamed, sorted, deactivated, and reactivated through the existing backend route. The `code` and `is_system` fields remain read-only after creation.

## Data Flow

1. Admin opens `/admin/config`; the existing page loads the bootstrap payload.
2. Admin opens an edit dialog or creates an option/status from a panel.
3. The panel validates and trims local form data.
4. The panel calls a Pinia store action such as `configuration.updateFamilyMember`.
5. The store calls the typed API helper, then reloads the bootstrap payload.
6. The refreshed payload updates every panel that depends on configuration data.

## Error Handling

Frontend validation catches required fields before the request. Backend validation remains the source of truth for invalid parents, missing records, duplicate codes, duplicate option values, and permission failures. Panels display `getChineseErrorMessage(error)` in `ElMessage.error`, following existing admin UI patterns.

Dialogs keep their saving states independent so a slow save in one editor does not disable unrelated create forms. Dialog state is cleared on close to avoid stale record data.

## Testing

Frontend type contracts will verify all new payload types, API helpers, and store actions compile against the existing route shapes.

Source/runtime contracts will verify that:

- location, member, category, field, attribute option, and item status edit flows are wired to store actions;
- active switches are present for editable entities;
- immutable fields such as category code, field key, item status code, and attribute option value are not sent in update payloads;
- dictionary groups/options remain read-only in this slice.

Existing backend configuration API tests continue to cover the PATCH route behavior. The final verification will run the frontend contract checks, `vue-tsc`, the frontend build, and focused backend configuration tests.

## Rollout

The feature is additive and uses existing permissions. Users without `config:manage` already cannot access configuration writes. No database migration is required. If any edge case appears in production, disabling the new UI actions is enough to fall back to the prior create/read behavior.
