# HomeVault Phase 4 Closeout

Date: 2026-07-01
Branch checked: `phase-1-foundation`

This document records the current project closeout after Phase 4C-4. It is a status and handoff document only; it does not introduce new business behavior.

## Current Completion Status

### Phase 1: Foundation

Complete.

- FastAPI backend foundation, SQLite migrations, structured error handling, and app bootstrap.
- Token login, session persistence, logout, and RBAC permission checks.
- Vue 3 / Element Plus frontend shell with authenticated layout, route guards, and permission-gated navigation.

### Phase 2: Core Configuration

Complete.

- Home space, residence, location tree, family members, categories, custom attribute definitions, attribute options, item statuses, and dictionary bootstrap data.
- Phase 2's known active-residence-name limitation is resolved by Phase 4C-1. No active Phase 2 known limitations remain.

### Phase 3: Inventory

Complete for the planned first inventory scope.

- Item create/edit/detail/list workflows.
- Card and table views, search and filtering.
- Images, attachments, tags, ownership, keeper, location/container placement, and privacy level.
- Status changes, movement history, quantity history, loans, returns, and archive handling.
- `privacy_level=sensitive` is enforced as a visibility boundary for non-admin users.

### Phase 4A: Reminders

Complete for the planned reminder-center scope.

- Persisted reminders, reminder center page, filters, and detail modal.
- Manual reminders and item-linked reminders.
- Loan-return reminder automation.
- Complete, dismiss, reopen, archive, and related item navigation flows.

### Phase 4B: Audit Logs

Complete for the planned audit-log scope.

- Audit log model, migration, service helper, and query API.
- Audit writes for authentication, user management, and configuration mutations covered by the 4B plan.
- Audit log frontend page with list filters and detail dialog.
- `logs:view` permission gates the API, route, and navigation.

### Phase 4C: Management Enhancements

Complete through 4C-4.

- 4C-1: admin user management, system role visibility, role assignment, last-active-admin guard, and residence active-only uniqueness/editing.
- 4C-2: configuration management polish for residences, locations, family members, categories, custom fields, attribute options, and item statuses.
- 4C-3: inventory bulk operations and CSV export.
- 4C-4: safe create-only inventory CSV import with template download, preview validation, one-time confirmation tokens, and frontend import dialog.

## Deliberately Deferred Work

These are not current-phase defects. They are intentionally outside the implemented slices and should get their own spec/plan before implementation.

- Custom role management: create/edit/deactivate non-system roles and assign permission sets.
- Permission editing: keep system permission codes carefully controlled; do not make them ad hoc without a separate security design.
- Dictionary group and dictionary option editing: currently read-only by design. Item statuses are editable, but generic dictionary groups/options are not.
- Import updates/merges: 4C-4 import is create-only. It does not update existing items, merge duplicates, import images, or import attachments.
- QR code and scan workflows.
- WeChat mini program, WeChat login, and external notification channels.
- Reminder recurrence, snooze, and broader household-task reminder sources.
- Formal end-to-end browser CI. Current verification relies on backend tests, frontend contracts, type checks, and build checks.

## Current Risk Boundaries

- Role model: `admin`, `editor`, and `viewer` remain system-defined. Users can be assigned roles, but roles themselves are not yet user-editable.
- Permissions: permissions are seeded application capabilities, not administrator-created records.
- Dictionary records: dictionary groups/options are exposed for reading and bootstrapping workflows; editing remains out of scope.
- CSV import: preview tokens are in memory and time-limited, so previews do not survive backend restart. This is acceptable for the current local-first workflow.
- Audit coverage: key mutation flows are covered. If new mutable features are added, their service layer should explicitly write audit events.
- Media import: images and attachments stay in the interactive item form/media uploader path.

## Suggested Next Slices

Recommended order:

1. Phase 4C-5 custom role management, conservative version: system permissions remain fixed; only custom non-system roles are editable.
2. Dictionary group/option editing if the product needs configurable dictionaries beyond item statuses and attribute options.
3. Import/export v2 for update/merge strategy and media handling.
4. Browser-based E2E acceptance suite for login, configuration, inventory, reminders, audit logs, import, and bulk workflows.
5. QR code, mobile, and external notification integrations.

## Verification Record

Last verification: 2026-07-01.

Commands run:

```powershell
Set-Location F:\HomeVault\backend
python -m pytest -q

Set-Location F:\HomeVault\frontend
Get-ChildItem -Path .\tests -Filter *.mjs | ForEach-Object { node $_.FullName }
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
npm.cmd run build

Set-Location F:\HomeVault
git diff --check
git status --short --branch
```

Results:

- Backend `python -m pytest -q`: `186 passed, 1 warning`. The warning is the existing Starlette `TestClient` / `httpx` deprecation warning.
- Frontend `.mjs` contract/runtime checks: exit code 0.
- Frontend `vue-tsc --noEmit -p tsconfig.contract.json`: exit code 0.
- Frontend `npm.cmd run build`: exit code 0. Existing Vite/Rollup warnings remain for VueUse pure annotations and large chunks.
- `git diff --check`: exit code 0.
- `git status --short --branch` before committing this closeout: branch `phase-1-foundation` matched `origin/phase-1-foundation`; only this new closeout document was untracked.

No browser-based manual acceptance run was performed as part of this closeout pass.
