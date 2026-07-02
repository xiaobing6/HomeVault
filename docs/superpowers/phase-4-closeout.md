# HomeVault Phase 4 Closeout

Date: 2026-07-02
Branch checked: `phase-1-foundation`

This document records the current project closeout after Phase 4C-5 and the dictionary-backed importance/location-type follow-up. It is a status and handoff document only; it does not introduce new business behavior.

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
- Dictionary-backed item importance in create/edit/detail/list/filter/import/export flows.
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

Complete through 4C-5.

- 4C-1: admin user management, system role visibility, role assignment, last-active-admin guard, and residence active-only uniqueness/editing.
- 4C-2: configuration management polish for residences, locations, family members, categories, custom fields, attribute options, and item statuses.
- 4C-3: inventory bulk operations and CSV export.
- 4C-4: safe create-only inventory CSV import with template download, preview validation, one-time confirmation tokens, and frontend import dialog.
- 4C-5: custom role management with read-only system permissions, read-only built-in roles, custom role create/edit/activate/deactivate, active-role assignment, and role mutation audit logging.
- Dictionary follow-up: item importance and location node types are dictionary-backed; administrators can edit existing dictionary option labels, sort order, and active state.

## Deliberately Deferred Work

These are not current-phase defects. They are intentionally outside the implemented slices and should get their own spec/plan before implementation.

- Permission-code editing remains deferred. Permission codes are still system-owned and are not administrator-created records.
- Full dictionary management remains deferred. Existing dictionary option labels, sort order, and active state are editable, but dictionary group creation/deletion, option creation/deletion, option value changes, and group membership changes remain out of scope.
- Import updates/merges: 4C-4 import is create-only. It does not update existing items, merge duplicates, import images, or import attachments.
- QR code and scan workflows.
- WeChat mini program, WeChat login, and external notification channels.
- Reminder recurrence, snooze, and broader household-task reminder sources.
- Formal end-to-end browser CI. A repeatable local Playwright baseline exists under `e2e/`, but CI gating is not wired yet.

## Current Risk Boundaries

- Role model: `admin`, `editor`, and `viewer` remain system-defined and read-only. Custom non-system roles can be created, edited, activated, and deactivated.
- Permissions: permissions are seeded application capabilities, not administrator-created records.
- Dictionary records: existing option labels, sort order, and active state can be edited. Permission-like values, group creation/deletion, option creation/deletion, option value changes, and group membership changes remain system-owned.
- CSV import: preview tokens are in memory and time-limited, so previews do not survive backend restart. This is acceptable for the current local-first workflow.
- Audit coverage: key mutation flows are covered. If new mutable features are added, their service layer should explicitly write audit events.
- Media import: images and attachments stay in the interactive item form/media uploader path.

## Suggested Next Slices

Recommended order:

1. Import/export v2 for update/merge strategy and media handling.
2. Promote the local Playwright E2E baseline into CI and expand coverage beyond smoke acceptance.
3. Full dictionary management only if the product needs administrator-created dictionary groups/options.
4. QR code, mobile, and external notification integrations.

## Verification Record

Last verification: 2026-07-02.

Commands run:

```powershell
Set-Location F:\HomeVault\backend
python -m pytest -q

Set-Location F:\HomeVault\frontend
Get-ChildItem -Path .\tests -Filter *.mjs | ForEach-Object { node $_.FullName }
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
npm.cmd run build

Set-Location F:\HomeVault\e2e
npm.cmd test

Set-Location F:\HomeVault
git diff --check
git status --short --branch
```

Results:

- Backend `python -m pytest -q`: `212 passed, 1 warning`. The warning is the existing Starlette `TestClient` / `httpx` deprecation warning.
- Frontend `.mjs` contract/runtime checks: exit code 0.
- Frontend `vue-tsc --noEmit -p tsconfig.contract.json`: exit code 0.
- Frontend `npm.cmd run build`: exit code 0. Existing Vite/Rollup warnings remain for VueUse pure annotations and large chunks.
- E2E `npm.cmd test`: `2 passed`. The suite starts an isolated SQLite-backed backend, the Vite frontend, and Chromium via Playwright.
- `git diff --check`: exit code 0.
- `git status --short --branch`: branch `phase-1-foundation`; changes are the planned backend test fixes, closeout/plan docs, and new `e2e/` suite files.
