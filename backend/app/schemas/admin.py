from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.errors import bad_request


class RequestModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class AdminUserListQuery(RequestModel):
    search: str | None = Field(default=None, max_length=120)
    role: str | None = Field(default=None, max_length=80)
    is_active: bool | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AdminUserCreate(RequestModel):
    username: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=200)
    role_codes: list[str] = Field(min_length=1)

    @field_validator("role_codes", mode="before")
    @classmethod
    def ensure_role_codes_present(cls, value: object) -> object:
        if isinstance(value, list) and not value:
            raise bad_request("用户至少需要一个角色")
        return value


class AdminUserUpdate(RequestModel):
    display_name: str = Field(min_length=1, max_length=120)
    is_active: bool
    role_codes: list[str] = Field(min_length=1)

    @field_validator("role_codes", mode="before")
    @classmethod
    def ensure_role_codes_present(cls, value: object) -> object:
        if isinstance(value, list) and not value:
            raise bad_request("用户至少需要一个角色")
        return value


class AdminPasswordReset(RequestModel):
    password: str = Field(min_length=8, max_length=200)


class AdminPermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: str


class AdminRoleResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str
    is_system: bool
    permissions: list[AdminPermissionResponse] = Field(default_factory=list)


class AdminUserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    is_active: bool
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    page_size: int
