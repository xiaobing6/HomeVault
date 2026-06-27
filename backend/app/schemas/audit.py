from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogListQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    action: str | None = Field(default=None, max_length=120)
    resource_type: str | None = Field(default=None, max_length=80)
    result: str | None = Field(default=None, max_length=40)
    actor_user_id: int | None = None
    search: str | None = Field(default=None, max_length=120)
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AuditLogResponse(BaseModel):
    id: int
    occurred_at: datetime
    actor_user_id: int | None
    actor_username: str | None
    action: str
    resource_type: str
    resource_id: str | None
    resource_label: str | None
    result: str
    metadata: dict[str, Any] | None = None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
