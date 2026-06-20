# HomeVault Phase 4A Reminders Design

## Purpose

Phase 4A adds a standalone reminder system to HomeVault. The goal is to make upcoming and overdue household tasks visible without mixing reminder state into item, loan, or custom-field records.

The selected approach is option B from the design discussion: reminders are persisted in their own table. This gives HomeVault a durable reminder lifecycle now, while keeping room for later capabilities such as snoozing, external notifications, richer recurrence, and cross-module reminders.

Phase 4 is intentionally split:

- Phase 4A: reminder center, persisted reminders, reminder filters, and reminder detail modal.
- Phase 4B: global audit log and operation history UI.
- Phase 4C: management enhancements such as user and role screens, import/export, bulk operations, and the known inactive residence-name uniqueness migration.

## Scope

Phase 4A includes:

- A new persisted `reminders` model.
- API routes for listing, creating, updating, completing, dismissing, and deleting or archiving reminders.
- Reminder links to inventory items and item loans.
- Dynamic overdue and upcoming calculations based on reminder dates.
- A reminder center page in the frontend.
- A reminder detail modal instead of a separate detail route.
- Quick filters on the item workbench for items with pending, upcoming, or overdue reminders.
- Tests for reminder rules, filters, permissions, and core UI integration.

Phase 4A does not include:

- Global audit log UI.
- Full user and role management screens.
- External notification integrations such as email, SMS, WeChat, or push.
- Recurring reminder schedules.
- QR code workflows.
- Bulk import/export.
- Mobile app or mini-program screens.
- Automatic reminder generation from every custom date field.

## Backend Data Model

Phase 4A adds a `reminders` table. It belongs to the inventory domain but stays independent from item and loan tables.

Model fields:

- `id`.
- `title`.
- `description`.
- `source_type`.
- `item_id`.
- `loan_id`.
- `due_date`.
- `remind_at`.
- `status`.
- `priority`.
- `created_by_user_id`.
- `completed_by_user_id`.
- `dismissed_by_user_id`.
- `completed_at`.
- `dismissed_at`.
- `archived_at`.
- `created_at`.
- `updated_at`.

`source_type` starts with:

- `manual`: a user-created reminder, usually linked to an item.
- `loan_return`: a reminder linked to an active item loan.

Phase 4A creates `loan_return` reminders when a loan is created with an expected return date. If the expected return date changes, the active linked reminder is updated. When the loan is returned, the linked reminder is completed automatically.

`status` starts with:

- `pending`: the reminder still needs attention.
- `done`: the reminder was completed.
- `dismissed`: the user intentionally ignored it.

Overdue is not stored as a separate status. It is calculated from `due_date`, `remind_at`, `status`, and the current server date. This avoids stale persisted state.

## Business Rules

Pending reminders are visible in the normal reminder center. Done and dismissed reminders are hidden by default but can be included with filters.

A reminder is overdue when:

- It is pending.
- It has a `due_date`.
- The `due_date` is before today in the server timezone.

A reminder is upcoming when:

- It is pending.
- It has a `remind_at` or `due_date`.
- The relevant date falls inside the requested upcoming window.

The default upcoming window is 7 days. The API accepts a bounded window parameter, capped at 90 days, so the frontend can support common choices such as 7, 14, and 30 days without creating separate endpoints.

Manual reminders may link to an item, but the model allows reminders without an item so later phases can support broader household tasks. Phase 4A UI should primarily expose item-linked manual reminders.

Linked item data is read-only from the reminder modal. Editing the item still happens through the existing item detail and edit flows.

Deleting a reminder is a soft delete using `archived_at`. Completed and dismissed reminders remain queryable.

## API Design

All reminder routes live under `/api/reminders`.

Read operations require `items:view`. Mutating reminder operations require `items:edit`. Administrator-only access is not required for normal reminder use.

Routes:

- `GET /api/reminders`
  - Lists reminders with pagination.
  - Supports `status`, `source_type`, `item_id`, `loan_id`, `overdue`, `upcoming_days`, `include_archived`, `search`, and sorting.
  - Includes compact linked item and loan summaries for list display.

- `POST /api/reminders`
  - Creates a manual reminder.
  - Accepts title, description, item link, due date, reminder date, and priority.

- `GET /api/reminders/{id}`
  - Returns the full reminder detail payload for the modal.
  - Includes linked item summary, linked loan summary, and computed due state.

- `PATCH /api/reminders/{id}`
  - Updates editable fields on a manual reminder.
  - Linked loan-return reminders may allow limited edits such as title, description, remind date, and priority, but the linked loan and due date remain owned by the loan workflow.

- `POST /api/reminders/{id}/complete`
  - Marks a pending reminder as done.
  - Stores actor and completion timestamp.

- `POST /api/reminders/{id}/dismiss`
  - Marks a pending reminder as dismissed.
  - Stores actor and dismissal timestamp.

- `POST /api/reminders/{id}/reopen`
  - Changes a done or dismissed reminder back to pending.

- `DELETE /api/reminders/{id}`
  - Soft-deletes the reminder with `archived_at`.

Inventory list routes are extended with reminder filters:

- `has_pending_reminder`.
- `has_upcoming_reminder`.
- `has_overdue_reminder`.
- `reminder_upcoming_days`.

These filters only consider non-archived pending reminders linked to the item.

## Frontend Design

Phase 4A adds a reminder center page. The route should fit the existing app navigation and use the same authenticated layout as inventory and admin pages.

The reminder center contains:

- Summary chips or compact counters for pending, upcoming, overdue, done, and dismissed reminders.
- A list or table of reminders.
- Filters for status, source type, overdue, upcoming window, item, and search text.
- A create-manual-reminder action.
- A detail modal opened from a reminder row.

The detail modal shows:

- Reminder title, status, priority, and due state.
- Due date and reminder date.
- Description.
- Linked item summary with a button to open the existing item detail modal or navigate to the item workbench context.
- Linked loan summary when present.
- Actions: complete, dismiss, reopen, edit, and archive, depending on status and permission.

The item workbench filter panel gains reminder quick filters:

- Pending reminders.
- Upcoming reminders.
- Overdue reminders.

These filters use the extended item list API instead of duplicating filtering in the frontend.

## Data Flow

Manual reminder creation starts from the reminder center or an item detail context. The frontend sends a `POST /api/reminders` request. The backend validates the linked item, stores the reminder, and returns the persisted reminder with computed due state.

Loan reminders are driven by loan operations. Creating a loan with an expected return date creates or updates the linked `loan_return` reminder. Returning the loan completes that reminder. If a loan has no expected return date, no automatic reminder is created.

Reminder list pages read computed due state from the backend. The frontend should not independently decide whether a reminder is overdue except for presentation fallbacks.

Item quick filters ask the item list endpoint for items with linked reminders. The inventory service performs the join or subquery so frontend counts and list behavior stay consistent with reminder center behavior.

## Error Handling

The backend returns validation errors when:

- A linked item does not exist or is archived.
- A linked loan does not exist or does not belong to the linked item.
- A due date or reminder date is malformed.
- A user tries to mutate an archived reminder.
- A user tries to edit loan-owned fields on a `loan_return` reminder.

Completing, dismissing, or reopening an already archived reminder is rejected.

Completing an already done reminder and dismissing an already dismissed reminder may be treated as idempotent success to keep UI retries simple.

## Testing

Backend tests should cover:

- Manual reminder create, list, detail, update, complete, dismiss, reopen, and soft delete.
- Loan creation with expected return date creates a linked reminder.
- Loan return completes the linked reminder.
- Updating expected return date updates the linked active reminder.
- Overdue and upcoming filters.
- Item list filters for pending, upcoming, and overdue reminders.
- Permission boundaries for read and write operations.

Frontend tests and verification should cover:

- Reminder API client and store behavior.
- Reminder center rendering and filters.
- Detail modal actions.
- Item workbench quick filters.
- Production build.
- Browser smoke through login, reminder center list, detail modal, and one item reminder filter when browser tooling is available.

## Acceptance Criteria

Phase 4A is complete when:

- Reminders are persisted in their own table and migrated through Alembic.
- Users can create, view, update, complete, dismiss, reopen, and archive reminders.
- Loan expected-return reminders are linked to loan workflows.
- The reminder center supports pending, upcoming, overdue, done, and dismissed views.
- Reminder details open in a modal.
- The item workbench can filter items by pending, upcoming, and overdue reminders.
- Automated backend tests pass.
- Frontend build passes.
- A browser or equivalent smoke test verifies the main reminder flow.
