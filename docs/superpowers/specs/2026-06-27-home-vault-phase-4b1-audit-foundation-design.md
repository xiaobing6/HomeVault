# HomeVault Phase 4B-1 Audit Foundation Design

## Purpose

Phase 4B-1 builds the global audit log foundation for HomeVault. The goal is to make important administrative and configuration activity traceable before adding the full audit-log workbench UI in Phase 4B-2.

This slice intentionally stays backend-first. It creates durable audit records, query APIs, and write hooks for the most important operations. A rich frontend log page, export workflow, and bulk-management audit coverage remain later slices.

## Scope

Phase 4B-1 includes:

- A new persisted `audit_logs` model and Alembic migration.
- A backend audit service for recording and querying audit entries.
- Read-only audit API routes guarded by the existing `logs:view` permission.
- Audit writes for authentication, user management, and core configuration changes.
- Tests for model registration, migration behavior, service behavior, API permissions, and key operation logging.

Phase 4B-1 does not include:

- A frontend audit log page. That is Phase 4B-2.
- CSV/Excel export. That belongs with later import/export management work.
- Bulk operation audit coverage.
- Custom role creation or permission editing.
- Full inventory, reminder, and media audit coverage. Those can be expanded after the audit foundation is stable.
- Recording passwords, tokens, full request bodies, or sensitive before/after payloads.

## Backend Data Model

Add an `audit_logs` table.

Fields:

- `id`: integer primary key.
- `occurred_at`: timezone-aware timestamp, defaulting to current UTC time.
- `actor_user_id`: nullable foreign key to `users.id` with `ON DELETE SET NULL`.
- `actor_username`: nullable string snapshot of the actor username at the time of the event.
- `action`: short machine-readable action code such as `auth.login`, `admin.user.create`, or `config.residence.update`.
- `resource_type`: short resource family such as `auth_session`, `user`, or `residence`.
- `resource_id`: nullable string resource identifier. Use string to support numeric ids and future external identifiers.
- `resource_label`: nullable human-readable resource label such as username or residence name.
- `result`: short status string. Phase 4B-1 starts with `success` and `failure`.
- `metadata`: nullable JSON object containing safe contextual fields.

Indexes:

- `occurred_at` descending or normal index for time-ordered list queries.
- `action`.
- `resource_type`.
- `actor_user_id`.
- `result`.

The model belongs in its own audit module so inventory and configuration domains do not own global history.

## Audit Events

Phase 4B-1 records these events:

- `auth.login`
  - Success and failure.
  - On success, store actor id and username.
  - On failure, store the attempted username in safe metadata, not as a user actor.
- `auth.logout`
  - Success when a valid active session is revoked.
- `admin.user.create`
  - Success when a user is created.
  - Resource is the created user.
- `admin.user.update`
  - Success when display name, active state, or roles are changed.
  - Metadata may include changed field names and role codes after the update.
- `admin.user.reset_password`
  - Success when an admin resets a user password.
  - Metadata must not include the password.
- `config.residence.create`
  - Success when a residence is created.
- `config.residence.update`
  - Success when a residence is updated, including activation changes.
- `config.location.create`
  - Success when a location node is created.
- `config.family_member.create`
  - Success when a family member is created.
- `config.category.create`
  - Success when an item category is created.
- `config.attribute_definition.create`
  - Success when a custom attribute definition is created.

Failures are required for login because failed login attempts are security-relevant. Other failure logging can be added later if it would require broad exception wrappers.

## Service Design

Create an audit service with two responsibilities:

1. `record_audit_log`
   - Accepts the database session, actor user or actor fields, action, resource fields, result, and safe metadata.
   - Adds an `AuditLog` row to the current transaction.
   - Does not commit on its own. The caller's existing transaction controls atomicity.
   - Sanitizes metadata to basic JSON-compatible values.

2. `list_audit_logs` and `get_audit_log`
   - Provide paginated querying for the API.
   - Support filtering by action, resource type, result, actor id, date range, and search text.
   - Return newest records first.

Audit writes should not break the business operation when metadata is empty or optional actor information is missing. They should still fail with the transaction if database insertion fails, because audit persistence is part of the operation for this slice.

## API Design

Add routes under `/api/audit`.

- `GET /api/audit/logs`
  - Requires `logs:view`.
  - Supports `action`, `resource_type`, `result`, `actor_user_id`, `search`, `occurred_from`, `occurred_to`, `page`, and `page_size`.
  - Returns `{ items, total, page, page_size }`.

- `GET /api/audit/logs/{log_id}`
  - Requires `logs:view`.
  - Returns one full audit log entry.
  - Returns the existing not-found error shape when missing.

Editors and viewers must receive forbidden responses from both routes unless they have `logs:view`.

## Frontend Contract For Later Slices

Phase 4B-1 does not build the UI page, but it should define typed frontend API helpers so Phase 4B-2 can use a stable contract.

Create `frontend/src/api/audit.ts` with:

- `AuditLogEntry`.
- `AuditLogFilters`.
- `AuditLogListResponse`.
- `listAuditLogsApi`.
- `getAuditLogApi`.

Add a lightweight TypeScript contract test that imports those helpers and confirms route payload shapes compile. Do not add navigation or a visible page in this slice.

## Data Flow

Authentication flow:

1. Login route receives credentials.
2. Failed credential validation records `auth.login` with `failure` and attempted username metadata.
3. Successful login creates the auth session, records `auth.login` with `success`, and commits.
4. Logout route revokes the session, records `auth.logout`, and commits.

Admin user flow:

1. Admin route receives the authenticated actor from `require_permission("users:manage")`.
2. Service performs create, update, or password reset.
3. Service records an audit event in the same transaction before commit.
4. The response returns the normal admin-user payload.

Configuration flow:

1. Configuration route receives an authenticated actor with `config:manage`.
2. Service creates or updates the configuration entity.
3. Service records an audit event in the same transaction before commit.
4. The response returns the normal configuration payload.

## Permission Model

- `logs:view` gates all audit read APIs.
- Audit writing is internal and follows the permission of the business operation being executed.
- `users:manage` remains the permission for user management.
- `config:manage` remains the permission for configuration mutations.
- `items:view`, `items:edit`, and reminder permissions are not changed in Phase 4B-1.

## Privacy And Safety

Audit metadata must not store:

- Passwords.
- Access tokens.
- Password hashes.
- Full request bodies.
- Uploaded file contents.
- Personally sensitive freeform values beyond existing labels that are already visible in the app.

Allowed metadata examples:

- Changed field names.
- New role code list for user role updates.
- Residence active state after update.
- Attempted username for failed login.
- Pagination/filter context is not recorded.

## Error Handling

Audit read APIs use the existing backend error response shape.

Expected behaviors:

- Unauthorized requests return the existing auth error.
- Requests without `logs:view` return the existing forbidden message.
- Missing log detail returns `日志不存在`.
- Invalid date or pagination values use normal FastAPI/Pydantic validation responses.

Audit writes are part of the same transaction as the operation. If the audit insert fails, the operation should roll back rather than silently succeeding without an audit trail.

## Testing Strategy

Backend tests:

- Model test confirms `audit_logs` is registered and can persist actor/resource metadata.
- Migration test confirms Alembic upgrade and downgrade include/remove `audit_logs`.
- Service tests cover recording, pagination, filters, search, and detail not-found behavior.
- API tests cover admin access and viewer/editor forbidden responses.
- Auth API tests confirm successful login, failed login, and logout write audit entries.
- Admin user API tests confirm create, update, and password reset write audit entries.
- Configuration API tests confirm residence create/update and core create operations write audit entries.

Frontend tests:

- Type contract imports `AuditLogEntry`, `AuditLogFilters`, `AuditLogListResponse`, `listAuditLogsApi`, and `getAuditLogApi`.
- Source contract ensures Phase 4B-1 does not add a visible `/admin/logs` route yet.
- Existing frontend contracts and production build still pass.

Full verification before completion:

- `python -m pytest -v`
- `node .\tests\audit-contract.mjs`
- `.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json`
- `npm.cmd run build`
- Existing frontend source/runtime contracts from earlier phases.

## Acceptance Criteria

Phase 4B-1 is complete when:

- `audit_logs` exists after migration and is removed on downgrade.
- Audit entries can be recorded and queried through service functions.
- Admin users with `logs:view` can list and view audit entries through `/api/audit/logs`.
- Viewer/editor users without `logs:view` cannot read audit entries.
- Login success, login failure, logout, user management mutations, and core configuration mutations create audit entries.
- Passwords, tokens, password hashes, and full request bodies are not stored in audit metadata.
- Frontend typed audit API helpers compile.
- Existing Phase 1, Phase 2, Phase 3, Phase 4A, and Phase 4C-1 tests still pass.
