# HomeVault Phase 4C-3 Bulk Inventory Operations and CSV Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add practical inventory batch workflows for selected items and filtered CSV export while preserving existing permission, privacy, and history behavior.

**Architecture:** Extend the existing inventory API instead of creating a separate batch subsystem. Backend batch services validate all target items first, then write movement/status/archive changes in one transaction and reuse the current response/privacy builders. Frontend adds table selection, toolbar batch actions, typed API/store actions, and compact Element Plus dialogs.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, Vue 3, TypeScript, Pinia, Element Plus, Axios.

---

## File Structure

- Modify `backend/app/schemas/inventory.py`: add bulk request/response and export request schemas.
- Modify `backend/app/services/inventory.py`: add bulk move/status/archive services and CSV export generation.
- Modify `backend/app/api/routes/inventory.py`: add bulk endpoints and export endpoint with existing permissions.
- Modify `backend/tests/test_inventory_api.py`: cover batch mutation permissions/history and CSV privacy behavior.
- Modify `frontend/src/api/inventory.ts`: add typed bulk/export payloads and API helpers.
- Modify `frontend/src/stores/inventory.ts`: add store actions that refresh inventory after batch mutations.
- Modify `frontend/src/components/items/ItemTable.vue`: add multi-select column and selection event.
- Modify `frontend/src/components/items/ItemToolbar.vue`: add selected-count, bulk buttons, and export buttons.
- Modify `frontend/src/pages/ItemsPage.vue`: maintain selected rows and show batch dialogs.
- Create `frontend/tests/inventory-bulk-export-contract.mjs`: source-level checks for UI/API/store wiring.

## Task 1: Backend Contracts

- [ ] Add failing pytest coverage for bulk move/status/archive APIs.
- [ ] Add failing pytest coverage for CSV export by selected ids and current filters.
- [ ] Assert `items:edit`, `items:archive`, and `items:view` permissions are enforced by route dependencies.
- [ ] Assert CSV export uses current privacy redaction for `privacy_level=sensitive`.

## Task 2: Backend Implementation

- [ ] Add Pydantic request/response models with item id validation and batch size caps.
- [ ] Add service helpers that load all requested items, fail on missing ids, and commit once.
- [ ] Reuse current placement/status validation and movement history creation.
- [ ] Add CSV generation from selected ids or unpaginated filters.
- [ ] Return CSV with `text/csv; charset=utf-8` and an attachment filename.

## Task 3: Frontend Contracts

- [ ] Add source-level contract checks for API helpers, store actions, table selection, toolbar buttons, and page wiring.
- [ ] Run the contract before implementation and confirm it fails.

## Task 4: Frontend Implementation

- [ ] Add API payloads and helpers for bulk move/status/archive/export.
- [ ] Add store methods and refresh inventory after successful batch mutations.
- [ ] Add table selection and clear stale selections when the list changes.
- [ ] Add toolbar actions for selected bulk operations and CSV export.
- [ ] Add batch dialogs for status, move, and archive using existing configuration data.
- [ ] Download exported CSV in the browser without leaving the page.

## Task 5: Verification

- [ ] Run targeted backend tests for inventory APIs.
- [ ] Run frontend contract tests.
- [ ] Run type/build verification for frontend.
- [ ] Run broader regression tests if targeted checks pass.
