# Repository Guidelines

## Project Structure & Module Organization

HomeVault is split into a FastAPI backend and a Vue 3 frontend. Backend code lives in `backend/app`, grouped by `api`, `core`, `db`, `models`, `schemas`, and `services`; migrations are in `backend/alembic/versions`, and pytest tests are in `backend/tests`. Frontend code lives in `frontend/src`, with components, pages, stores, API clients, router setup, and styles in matching subfolders. Frontend contracts are in `frontend/tests`, Playwright tests are in `e2e`, and planning notes live in `docs/superpowers`.

## Build, Test, and Development Commands

- `cd backend; python -m pip install -e ".[dev]"`: install backend dev dependencies.
- `cd backend; python -m alembic upgrade head`: apply migrations.
- `cd backend; python -m app.cli`: seed default data.
- `cd backend; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`: run the API.
- `cd backend; python -m pytest -v`: run backend tests.
- `cd frontend; npm install; npm run dev`: install dependencies and start Vite on `127.0.0.1:5173`.
- `cd frontend; npm run build`: type-check and build the frontend.
- `cd frontend; npx vue-tsc -p tsconfig.contract.json`: run TypeScript contracts.
- `cd e2e; npm install; npm test`: run Playwright acceptance tests.

## Coding Style & Naming Conventions

Use 4-space indentation for Python and 2-space indentation for TypeScript/Vue. Keep backend route handlers in `api/routes`, business logic in `services`, persistence models in `models`, and request/response types in `schemas`. Name Python tests `test_*.py`. Use PascalCase for Vue components/pages, camelCase for TypeScript functions and store actions, and descriptive contract names such as `admin-users-contract.ts`.

## Testing Guidelines

Add or update tests near the changed behavior. Backend API, service, schema, and model changes need pytest coverage in `backend/tests`. Frontend API/store/type contracts belong in `frontend/tests`; UI structure checks often use `.mjs` source inspections. End-to-end flows go in `e2e/tests/*.spec.ts`. Run the smallest relevant suite first, then the broader build or e2e check.

## Commit & Pull Request Guidelines

Recent history mostly uses concise Conventional Commit prefixes such as `feat:`, `fix:`, and `test:`, with occasional short Chinese summaries. Keep commits scoped to one change. Pull requests should include a behavior summary, test results, linked issue or design note when applicable, and screenshots for visible UI changes. Call out migrations, seed-data changes, or new environment variables.

## Security & Configuration Tips

Use `backend/.env.example` as the template for local settings, and never commit real secrets or personal data. Treat `uploads`, `output`, local SQLite databases, and Playwright artifacts as generated data.
