# HomeVault Phase 4C-1 Management Foundation Design

## Purpose

Phase 4C-1 builds the management foundation that should exist before the global audit log is expanded. It keeps Phase 4B from growing into a user-management project by creating the core user and role surfaces first, while leaving audit logging, import/export, and bulk operations for later slices.

## Scope

Phase 4C-1 includes:

- User management APIs and UI for administrators with `users:manage`.
- System role visibility and user role assignment.
- User creation, profile update, activation/deactivation, and password reset.
- Lockout guards so the last active administrator cannot be disabled or lose the `admin` role.
- The known Phase 2 residence-name migration: active residences must have unique names, while inactive residence names may be reused.
- Residence management polish needed to use that rule from the UI: edit basic residence fields and activate/deactivate residences.

Phase 4C-1 does not include:

- Global audit log storage or UI. That remains Phase 4B after these management operations exist.
- Custom role creation or permission editing. Roles stay system-defined in this slice.
- Import/export, bulk operations, QR code workflows, mobile-specific screens, or external notifications.
- Full soft-delete polish for every configuration entity. This slice fixes residence management because it is tied to the known migration.

## Backend Design

### User And Role API

Add an admin route group under `/api/admin`.

- `GET /api/admin/users`
  - Requires `users:manage`.
  - Returns users with id, username, display name, active state, roles, permissions, created time, and updated time.
  - Supports `search`, `role`, `is_active`, `page`, and `page_size`.
- `POST /api/admin/users`
  - Requires `users:manage`.
  - Creates a local password user.
  - Requires unique username, non-empty display name, password, and at least one valid role code.
  - Hashes the password with the existing security helper.
- `PATCH /api/admin/users/{user_id}`
  - Requires `users:manage`.
  - Updates display name, active state, and role codes.
  - Rejects changes that would leave no active admin user.
- `POST /api/admin/users/{user_id}/reset-password`
  - Requires `users:manage`.
  - Replaces the password hash.
- `GET /api/admin/roles`
  - Requires `users:manage`.
  - Returns system roles and their permission codes/names/descriptions.

The backend keeps role definitions seeded by `app.services.seed`. It does not expose role creation, role deletion, or permission mutation.

### Lockout Guard

The service layer must reject these operations:

- Deactivating the only active user with the `admin` role.
- Removing the `admin` role from the only active admin user.
- Creating or updating a user with unknown role codes.
- Creating or updating a user with no roles.

The guard is service-level, not only route-level, so tests can exercise it directly.

### Residence Active-Only Uniqueness

The existing Phase 2 model enforces `residences.name` as globally unique. Phase 4C-1 changes this to active-only uniqueness:

- The SQLAlchemy model removes global `unique=True` from `Residence.name`.
- The migration replaces global uniqueness with a partial unique index for active residences.
- The service layer checks active-name conflicts before create and update.
- Inactive records can keep or reuse a name that exists on another inactive record.
- Reactivating or renaming a residence to a name already used by another active residence is rejected with a Chinese bad-request message.

For SQLite, the migration must be written so existing databases can upgrade safely even though SQLite cannot drop every generated unique constraint directly. A table-rebuild migration is acceptable if it preserves existing residence ids and foreign keys.

### Residence Management API

The existing configuration routes already have create and update endpoints for residences. Phase 4C-1 keeps those endpoints and adjusts their behavior to the new uniqueness rule. No separate residence route group is needed.

## Frontend Design

### Navigation

The authenticated layout gains a user-management entry visible only with `users:manage`. The existing `/admin/config` page remains for core configuration. A new route `/admin/users` loads the user management page and is guarded by `users:manage`.

### User Management Page

Create `AdminUsersPage.vue` as a dense operational page, not a landing page.

The page contains:

- Search input for username/display name.
- Role filter and active-state filter.
- Users table with username, display name, roles, active state, created time, updated time, and actions.
- Create/edit dialog for display name, username on create, active switch, role checkboxes, and password on create.
- Reset-password dialog with password confirmation.
- Role reference panel or tab listing each system role and its permissions.

The page uses Element Plus tables, dialogs, tags, switches, segmented filters, and existing permission patterns. It does not create custom cards inside cards.

### Residence Panel Polish

`ResidenceLocationPanel.vue` gains edit support for existing residences:

- Open an edit dialog from the residence table.
- Update name, description, address, sort order, and active state.
- Show active/inactive tags clearly.
- Keep location creation tied to an existing residence.

This polish exists specifically to make the active-only uniqueness migration usable. Broader configuration editing remains outside this slice unless it is already present.

## Data Flow

User management:

1. Admin opens `/admin/users`.
2. Frontend loads users and roles through typed admin API helpers.
3. Create/update/reset actions call admin endpoints.
4. Store or page state reloads the current page after a successful mutation.
5. Errors use the existing `getChineseErrorMessage` helper.

Residence management:

1. Admin opens `/admin/config`.
2. Existing configuration bootstrap loads residences.
3. Edit residence dialog submits the existing PATCH endpoint.
4. Configuration store reloads bootstrap data after success.

## Permission Model

- `users:manage` gates all user and role management routes and UI.
- Existing `config:manage` continues to gate residence configuration writes.
- `items:view` remains sufficient for reading configuration bootstrap data where existing item workflows need it.
- `logs:view` is not used by this slice.

## Error Handling

Backend errors should return the existing `{ "message": "..." }` shape. Required messages:

- Unknown role: `角色不存在`
- Empty role set: `用户至少需要一个角色`
- Username conflict: `账号已存在`
- Last admin lockout: `至少保留一个启用的管理员`
- Active residence name conflict: `启用住宅名称已存在`

## Testing Strategy

Backend tests:

- User model/service tests for create, update, reset password, role assignment, and last-admin guard.
- User API tests for admin access and viewer/editor forbidden responses.
- Migration/model tests for active-only residence-name uniqueness.
- Configuration service tests for inactive-name reuse and active-name conflict.

Frontend tests:

- Type contract test importing the admin API, store/page, and router route.
- Source contract test checking the protected `/admin/users` route and layout navigation permission.
- Build verification with `npm.cmd run build`.

Full verification before completion:

- `python -m pytest -v`
- `node .\tests\admin-users-contract.mjs`
- `node .\tests\admin-users-ui-contract.mjs`
- `.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json`
- `npm.cmd run build`

## Acceptance Criteria

Phase 4C-1 is complete when:

- Admin can list users and roles.
- Admin can create a user, assign existing roles, deactivate/reactivate a user, and reset a password.
- Viewer/editor cannot access user management APIs or UI routes.
- The system prevents removing or disabling the last active admin.
- An inactive residence name can be reused by another residence.
- Two active residences cannot share a name.
- Admin can edit and deactivate/reactivate residences from the configuration UI.
- Existing Phase 1, Phase 2, Phase 3, and Phase 4A tests still pass.
