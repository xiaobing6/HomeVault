from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.reminders import ReminderCreate, ReminderDetailResponse, ReminderListQuery


def test_reminder_create_requires_non_blank_title() -> None:
    with pytest.raises(ValidationError):
        ReminderCreate(title="   ")


def test_reminder_list_query_bounds_upcoming_days() -> None:
    assert ReminderListQuery().upcoming_days is None
    assert ReminderListQuery(upcoming_days=90).upcoming_days == 90
    with pytest.raises(ValidationError):
        ReminderListQuery(upcoming_days=0)
    with pytest.raises(ValidationError):
        ReminderListQuery(upcoming_days=91)


def test_reminder_detail_response_serializes_computed_state() -> None:
    now = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)
    response = ReminderDetailResponse(
        id=1,
        title="Return Passport",
        description="Check with Taylor",
        source_type="loan_return",
        item_id=2,
        loan_id=3,
        due_date=date(2026, 6, 21),
        remind_at=date(2026, 6, 20),
        status="pending",
        priority="high",
        due_state="upcoming",
        days_until_due=1,
        created_by_user_id=4,
        completed_by_user_id=None,
        dismissed_by_user_id=None,
        completed_at=None,
        dismissed_at=None,
        archived_at=None,
        created_at=now,
        updated_at=now,
        item={"id": 2, "name": "Passport", "is_archived": False},
        loan={"id": 3, "borrower_name": "Taylor", "expected_return_date": date(2026, 6, 21), "returned_at": None},
    )
    assert response.due_state == "upcoming"
    assert response.item is not None
    assert response.loan is not None
