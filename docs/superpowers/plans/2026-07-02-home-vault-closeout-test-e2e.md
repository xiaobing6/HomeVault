# HomeVault Closeout Test And E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for test or behavior changes. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the current backend regression tests, update the Phase 4 closeout status, and add a repeatable browser E2E baseline.

**Architecture:** Keep production validation unchanged. Repair stale backend tests by giving service fixtures the same core dictionary data that API fixtures already receive, then add a versioned Playwright suite that boots an isolated SQLite database and local backend/frontend servers.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest, Vue 3, Vite, Element Plus, Playwright.

---

## File Structure

- Modify `backend/tests/test_inventory_schemas.py`: add `importance` to hand-built response payloads.
- Modify `backend/tests/test_inventory_services.py`: seed the core dictionary before service-level inventory tests create items.
- Modify `docs/superpowers/phase-4-closeout.md`: update dictionary-option status and verification record.
- Create `e2e/package.json`: Playwright package scripts.
- Create `e2e/playwright.config.ts`: web server and project configuration.
- Create `e2e/scripts/backend-server.mjs`: prepare isolated DB, seed baseline data, and start the backend.
- Create `e2e/scripts/seed-e2e-data.py`: add stable residence, location, member, category, and item data.
- Create `e2e/tests/acceptance.spec.ts`: browser acceptance coverage for login, configuration, inventory, reminders, audit logs, import, and bulk surfaces.

## Task 1: Repair Backend Test Regression

- [ ] Add `importance: "medium"` to `ItemDetailResponse` and `ItemListResponse` payloads in `backend/tests/test_inventory_schemas.py`.
- [ ] Import `ensure_core_configuration_seed` in `backend/tests/test_inventory_services.py`.
- [ ] Call `ensure_core_configuration_seed(db_session)` at the start of `inventory_seed`.
- [ ] Run `python -m pytest tests/test_inventory_schemas.py tests/test_inventory_services.py -q` from `backend`.
- [ ] Run `python -m pytest -q` from `backend`.

## Task 2: Update Closeout Document

- [ ] Update `docs/superpowers/phase-4-closeout.md` so dictionary option editing is no longer listed as fully deferred.
- [ ] Record the fixed backend, frontend contract, and build verification results.

## Task 3: Add Browser E2E Baseline

- [ ] Add Playwright package and config under `e2e/`.
- [ ] Add backend boot script that recreates `e2e/.runtime/homevault-e2e.db`, runs Alembic, runs the app CLI seed, applies E2E data, and starts uvicorn.
- [ ] Add E2E data seed script using app models and services.
- [ ] Add acceptance specs for login, navigation, configuration, inventory import/export/bulk surfaces, reminder creation, and audit-log visibility.
- [ ] Run `npm install` from `e2e` if dependencies are not installed.
- [ ] Run `npm test` from `e2e`.
- [ ] Run `git diff --check` and `git status --short --branch` from the repo root.
