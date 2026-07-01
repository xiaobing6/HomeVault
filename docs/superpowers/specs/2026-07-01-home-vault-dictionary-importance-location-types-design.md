# HomeVault Dictionary Importance And Location Types Design

## Context

HomeVault already has dictionary groups and dictionary options as configuration data. The current core groups are `units`, `importance`, and `storage_conditions`, but only `units` is used by the item form. `importance` is present as a group without a business loop, and `storage_conditions` no longer fits the current product scope.

This design makes dictionary-backed fields useful without turning every select control into a dictionary. Dictionary groups are used only for low-risk, reusable candidate values. Workflow states, security levels, role permissions, reminder status, and field rendering types remain system-controlled enums or domain entities.

## Goals

- Add item importance as a built-in item field backed by the `importance` dictionary group.
- Use exactly three importance values: `high`, `medium`, and `low`, displayed as 高, 中, and 低.
- Remove `storage_conditions` from the core dictionary set and do not add storage condition behavior.
- Add a core `location_node_types` dictionary group for location type values.
- Replace the hard-coded location type select with enabled dictionary options.
- Let administrators edit existing dictionary option labels, active state, and sort order.
- Do not add dictionary group creation, dictionary option creation, or delete flows to the frontend.
- Keep reminder priority and other workflow enums unchanged.

## Non-Goals

- No configurable reminder priorities.
- No storage condition item field.
- No custom field type refactor.
- No permission or privacy-level dictionary conversion.
- No frontend create/delete controls for dictionary groups or dictionary options.
- No full inventory audit rewrite.

## Core Dictionary Data

The core dictionary groups are:

- `units`: existing unit candidates used by item quantity.
- `importance`: item importance.
- `location_node_types`: location type candidates.

`storage_conditions` is removed from the core list. If an existing database contains the system `storage_conditions` group, the migration or seed cleanup removes that group and its options because the project has no production data yet and no business references depend on it.

Default `importance` options:

| value | label | sort_order |
| --- | --- | --- |
| `high` | 高 | 10 |
| `medium` | 中 | 20 |
| `low` | 低 | 30 |

Default `location_node_types` options:

| value | label | sort_order |
| --- | --- | --- |
| `room` | 房间 | 10 |
| `area` | 区域 | 20 |
| `cabinet` | 柜子 | 30 |
| `shelf` | 架子 | 40 |
| `box` | 箱/盒 | 50 |
| `other` | 其他 | 60 |

Default `units` options are seeded so the existing unit dictionary has editable values in a new installation. The first option remains 件 so current item defaults keep working.

## Backend Design

### Item Importance

The `items` table gets a new non-null `importance` column with default `medium`. Existing rows are backfilled to `medium`.

Item schemas include `importance` on create, update, list summaries, details, import/export normalization where applicable, and filters. Item creation requires an enabled option in the `importance` group. Item update accepts the current stored importance even if that option was later disabled, so editing unrelated fields does not fail for historical records. Changing importance to a different value requires the target option to be enabled.

The item list query supports `importance`. CSV export includes importance as a readable label with a raw-value fallback for unknown historical values.

### Location Node Types

Location create and update validate `node_type` against enabled options in the `location_node_types` group. Updating a location without changing `node_type`, or sending the same stored value, is allowed even if that option was later disabled. This preserves old data while preventing new usage of disabled values.

Location responses may keep returning the stored `node_type` value. The frontend maps it to the dictionary label for display.

### Dictionary Option Editing

Backend adds an update operation for existing dictionary options. The editable fields are:

- `label`
- `sort_order`
- `is_active`

The option `value`, group membership, and system/custom group identity are not editable in this slice. This prevents accidental data remapping while still allowing display-name, ordering, and enablement changes.

Dictionary option updates write audit logs with enough metadata to see which fields changed. Item importance changes add a narrow audit event for `item.importance.update`; this does not expand the whole inventory module into full audit coverage.

Existing dictionary create endpoints are not expanded by this design. The frontend management surface does not expose create or delete controls.

## Frontend Design

### Configuration Dictionary Panel

The dictionary panel changes from read-only tables to editable existing rows:

- Label editing with save/cancel.
- Active toggle.
- Sort order editing.
- No add button.
- No delete button.
- No group creation UI.

After saving, configuration bootstrap data refreshes so item and location forms see the latest labels/order/active state.

### Item Workflows

Item create/edit includes an importance select sourced from enabled `importance` options. The default is `medium` when available, otherwise the first enabled option, with `medium` as a final fallback.

Item detail, table/list, filter panel, and CSV export show importance. The UI displays dictionary labels, not raw values. If an item has an unknown or inactive importance value, the UI falls back to the stored raw value instead of failing.

### Location Workflows

Residence/location management uses enabled `location_node_types` options for location type selects. Location tree labels and edit forms display dictionary labels when available.

Disabled location types are hidden from new selections. Existing records using a disabled type still display and can be edited without changing the type.

## Error Handling

- Missing required dictionary groups are treated as configuration errors in backend validation.
- Unknown or disabled new values return a 400 response with a field-specific message.
- Existing historical values are displayed with raw-value fallback.
- Frontend save failures show the backend message through the existing Element Plus message flow.

## Testing

Backend tests cover:

- Core dictionary seed creates `importance` and `location_node_types` options and no longer creates `storage_conditions`.
- Item model and migration include `importance` with default `medium`.
- Item create/update/list/detail/filter/export include importance.
- Item create rejects unknown or disabled importance.
- Item update allows unchanged disabled historical importance.
- Location create/update validate dictionary-backed `node_type`.
- Location update allows unchanged disabled historical `node_type`.
- Dictionary option label, active state, and sort order updates persist and write audit logs.

Frontend tests cover:

- Dictionary panel exposes edit/enable/sort controls but no add/delete controls.
- Item form uses dictionary-backed importance options.
- Item detail/table/filter display importance.
- Location type select uses dictionary options instead of the hard-coded list.
- Type checking and production build pass.

## Acceptance Criteria

- `storage_conditions` no longer appears as a core dictionary group in a fresh or migrated local database.
- Admin users can edit, enable/disable, and sort existing dictionary options.
- Admin users cannot create or delete dictionary groups/options from the frontend.
- Item importance is available in create/edit/detail/list/filter/export.
- Location type options come from `location_node_types`.
- Disabled dictionary values are not selectable for new values, but historical records remain readable and editable.
- The implementation passes backend tests, frontend contract/runtime checks, type checking, and build verification.
