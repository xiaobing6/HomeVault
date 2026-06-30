# HomeVault Phase 4C-5 Role Management Design

## Purpose

Phase 4C-5 adds custom role management and finer role assignment control. It keeps permission codes system-owned while letting administrators create practical custom roles by selecting from those fixed permissions.

This slice continues the Phase 4C management work without turning permissions into a dynamic rules engine. The goal is to make role assignment flexible enough for real household/admin workflows while preserving safe built-in defaults.

## Scope

Phase 4C-5 includes:

- A role-management tab inside the existing user-management page.
- Read-only display of system permissions.
- Read-only built-in roles: `admin`, `editor`, and `viewer`.
- Custom roles that can be created, edited, activated, and deactivated.
- Custom role permission assignment by selecting existing system permission codes.
- User role assignment that includes built-in roles and active custom roles.
- Last-active-admin protection for user role changes.
- Audit logging for role creation, role updates, role activation/deactivation, and user role changes.

Phase 4C-5 does not include:

- Creating, editing, deleting, or deactivating permission codes.
- Editing `admin`, `editor`, or `viewer`.
- Physically deleting roles.
- Field-level permissions, data-scope permissions, ownership-based access, or per-item ACLs.
- Changing frontend route permission codes.
- Splitting role management into a separate navigation entry.

## Permission Model

Permissions remain system-defined application capabilities. They are seeded by the backend and referenced by code in route guards, service guards, and frontend navigation.

The current permission codes remain:

- `items:view`
- `items:create`
- `items:edit`
- `items:archive`
- `config:manage`
- `users:manage`
- `logs:view`

The role-management UI may list permission names, descriptions, and codes, but it must not provide controls to create or delete permissions.

## Role Rules

### System Roles

The built-in roles are:

- `admin`
- `editor`
- `viewer`

They remain `is_system=true`.

System roles are read-only:

- no name edit;
- no description edit;
- no permission edit;
- no activation toggle;
- no delete action.

The seed process may continue to synchronize these system roles to their expected permission sets.

### Custom Roles

Custom roles use `is_system=false`.

Administrators with `users:manage` can:

- create a custom role with code, name, description, permission codes, and active state;
- update name, description, selected permissions, and active state;
- deactivate a custom role instead of deleting it;
- reactivate a deactivated custom role.

Custom role `code` is immutable after creation. This keeps audit history, user-role references, and UI labels stable.

Role codes must be unique, non-empty, trimmed, lowercase-friendly identifiers. The backend should reject empty codes, duplicate codes, unknown permission codes, and empty permission sets.

## User Assignment Rules

User creation and update can assign:

- built-in system roles;
- active custom roles.

Inactive custom roles must not be assignable to new or updated users. Existing users who already have an inactive custom role may still display that role in the table, but the edit dialog should not make the inactive role selectable unless the role is reactivated first.

The existing last-active-admin guard remains required:

- the system must keep at least one active user with the `admin` role;
- an administrator cannot deactivate the last active admin user;
- an administrator cannot remove `admin` from the last active admin user.

Because system `admin` is read-only, custom role editing cannot remove the system's only administrative access path.

## Backend Design

Use the existing admin route group under `/api/admin`.

### Existing Endpoints To Keep

- `GET /api/admin/users`
- `POST /api/admin/users`
- `PATCH /api/admin/users/{user_id}`
- `POST /api/admin/users/{user_id}/reset-password`
- `GET /api/admin/roles`

`GET /api/admin/roles` should continue to return all roles so the page can show both system and custom roles. It should include each role's active state once the model/API supports it.

### New Or Expanded Endpoints

- `POST /api/admin/roles`
  - Requires `users:manage`.
  - Creates a custom role.
  - Rejects attempts to create `admin`, `editor`, or `viewer` duplicates.
  - Requires at least one valid permission code.
  - Writes `admin.role.create`.

- `PATCH /api/admin/roles/{role_id}`
  - Requires `users:manage`.
  - Updates only custom roles.
  - Allows name, description, permission codes, and active state changes.
  - Rejects system roles.
  - Rejects unknown permission codes and empty permission sets.
  - Writes `admin.role.update` for name/description/permission changes.
  - Writes `admin.role.activate` or `admin.role.deactivate` when active state changes.

No role delete endpoint is added in this slice.

### Model And Migration

The `roles` table already has `code`, `name`, `description`, and `is_system`.

Add an `is_active` column:

- boolean;
- non-null;
- default true;
- existing roles backfilled to true.

This column is needed so custom roles can be retired without deleting historical relationships or audit context.

## Frontend Design

The existing `/admin/users` route remains the single management surface. The page becomes a two-tab operational workbench:

- `人员管理`
- `角色管理`

### 人员管理 Tab

The current user table, filters, create/edit dialog, and reset-password dialog move into the `人员管理` tab.

Role selection in user create/edit:

- includes built-in roles;
- includes active custom roles;
- excludes inactive custom roles from selectable options;
- displays role names and codes clearly;
- keeps current validation requiring at least one role.

If a user already has a role that is now inactive, the table still shows it. Editing that user should prompt the administrator to choose from currently assignable roles before saving.

### 角色管理 Tab

The role-management tab contains:

- system role table or section, read-only;
- custom role table with active/inactive state;
- create custom role button;
- edit custom role action;
- activate/deactivate action for custom roles;
- permission checkbox group inside create/edit dialog.

Permission checkboxes display:

- permission name;
- permission code;
- description.

System roles should visually signal read-only behavior. They should not show editable action buttons.

## Data Flow

1. Admin opens `/admin/users`.
2. Page loads users and roles.
3. `人员管理` tab uses active custom roles plus system roles for assignment.
4. `角色管理` tab lists system and custom roles from the same role payload.
5. Creating or updating a custom role calls the role API.
6. The store reloads roles after a role mutation.
7. The store reloads users if role changes can affect displayed role labels or assignable role options.
8. Errors are shown through the existing Chinese error helper.

## Audit Logging

Role mutations write audit logs in the same service transaction as the role change.

Required events:

- `admin.role.create`
- `admin.role.update`
- `admin.role.activate`
- `admin.role.deactivate`

Recommended metadata:

- `permission_codes`
- `changed_fields`
- `is_active`

User role changes continue to use `admin.user.update`. The existing `role_codes` metadata remains required, and `changed_fields` should include `role_codes` only when the effective role set changes.

## Error Handling

Backend errors should use the existing `{ "message": "..." }` shape.

Required error cases:

- system role update rejected;
- duplicate role code rejected;
- blank role code/name rejected;
- empty permission set rejected;
- unknown permission code rejected;
- inactive custom role assignment rejected;
- last-active-admin lockout rejected.

## Testing Strategy

Backend tests:

- custom role create/update/activate/deactivate API tests;
- system role update rejection;
- duplicate and blank role validation;
- unknown permission and empty permission validation;
- inactive custom role cannot be assigned to a user;
- active custom role can be assigned to a user;
- last-active-admin guard still holds;
- role mutation audit logs are written with expected metadata.

Frontend tests:

- admin API/store contract for role create/update payloads;
- source contract that `AdminUsersPage.vue` has `人员管理` and `角色管理` tabs;
- source contract that system roles are read-only and custom roles expose create/edit/activate/deactivate controls;
- source contract that role assignment filters inactive custom roles from selectable options;
- `vue-tsc` contract check;
- production build.

Full verification before completion:

- backend targeted admin tests;
- backend full pytest;
- frontend `.mjs` contracts;
- frontend TypeScript contract check;
- frontend production build;
- `git diff --check`.

## Acceptance Criteria

Phase 4C-5 is complete when:

- administrators can manage users and roles from two tabs on the existing user-management page;
- built-in `admin`, `editor`, and `viewer` roles are visible but read-only;
- permissions are visible and selectable but cannot be created, edited, or deleted;
- administrators can create and edit custom roles;
- administrators can activate and deactivate custom roles;
- active custom roles can be assigned to users;
- inactive custom roles cannot be newly assigned to users;
- the last active admin cannot be locked out;
- role mutations and user role changes are audited;
- existing Phase 1 through Phase 4C-4 tests still pass.
