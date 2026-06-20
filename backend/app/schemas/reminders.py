from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RequestModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class ReminderListQuery(RequestModel):
    status: str | None = None
    source_type: str | None = None
    item_id: int | None = None
    loan_id: int | None = None
    overdue: bool | None = None
    upcoming_days: int | None = Field(default=None, ge=1, le=90)
    include_archived: bool = False
    search: str | None = None
    sort: str = "due_asc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ReminderCreate(RequestModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = ""
    item_id: int | None = None
    due_date: date | None = None
    remind_at: date | None = None
    priority: str = "normal"


class ReminderUpdate(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    item_id: int | None = None
    due_date: date | None = None
    remind_at: date | None = None
    priority: str | None = None


class ReminderItemSummary(ResponseModel):
    id: int
    name: str
    is_archived: bool


class ReminderLoanSummary(ResponseModel):
    id: int
    borrower_name: str
    expected_return_date: date | None = None
    returned_at: datetime | None = None


class ReminderSummaryResponse(ResponseModel):
    id: int
    title: str
    description: str
    source_type: str
    item_id: int | None = None
    loan_id: int | None = None
    due_date: date | None = None
    remind_at: date | None = None
    status: str
    priority: str
    due_state: str
    days_until_due: int | None = None
    created_by_user_id: int | None = None
    completed_by_user_id: int | None = None
    dismissed_by_user_id: int | None = None
    completed_at: datetime | None = None
    dismissed_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    item: ReminderItemSummary | None = None
    loan: ReminderLoanSummary | None = None


class ReminderDetailResponse(ReminderSummaryResponse):
    pass


class ReminderListResponse(ResponseModel):
    items: list[ReminderSummaryResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
