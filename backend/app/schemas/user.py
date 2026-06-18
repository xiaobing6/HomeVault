from pydantic import BaseModel


class CurrentUserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    roles: list[str]
    permissions: list[str]
