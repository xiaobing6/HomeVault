from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HomeSpaceResponse(ResponseModel):
    id: int
    name: str
    description: str
    is_active: bool


class HomeSpaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=255)


class ResidenceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=255)
    address: str = Field(default="", max_length=255)
    sort_order: int = 0


class ResidenceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=255)
    address: str = Field(default="", max_length=255)
    sort_order: int = 0
    is_active: bool = True


class ResidenceResponse(ResidenceUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class LocationNodeCreate(BaseModel):
    residence_id: int
    parent_id: int | None = None
    name: str = Field(min_length=1, max_length=120)
    node_type: str = Field(default="area", max_length=40)
    icon: str = Field(default="", max_length=60)
    sort_order: int = 0
    note: str = Field(default="", max_length=255)


class LocationNodeUpdate(BaseModel):
    parent_id: int | None = None
    name: str = Field(min_length=1, max_length=120)
    node_type: str = Field(default="area", max_length=40)
    icon: str = Field(default="", max_length=60)
    sort_order: int = 0
    note: str = Field(default="", max_length=255)
    is_active: bool = True


class LocationNodeResponse(LocationNodeUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    residence_id: int
    children: list[LocationNodeResponse] = Field(default_factory=list)


class FamilyMemberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    relation: str = Field(default="", max_length=80)
    phone: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=255)


class FamilyMemberUpdate(FamilyMemberCreate):
    is_active: bool = True


class FamilyMemberResponse(FamilyMemberUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None


class CategoryCreate(BaseModel):
    parent_id: int | None = None
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    icon: str = Field(default="", max_length=60)
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    parent_id: int | None = None
    name: str = Field(min_length=1, max_length=120)
    icon: str = Field(default="", max_length=60)
    sort_order: int = 0
    is_active: bool = True


class CategoryResponse(CategoryUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    attribute_definitions: list[AttributeDefinitionResponse] = Field(default_factory=list)
    children: list[CategoryResponse] = Field(default_factory=list)


class AttributeDefinitionCreate(BaseModel):
    category_id: int
    key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    field_type: str = Field(min_length=1, max_length=40)
    default_value: str = ""
    privacy_level: str = "normal"
    is_required: bool = False
    is_filterable: bool = False
    sort_order: int = 0


class AttributeDefinitionUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    field_type: str = Field(min_length=1, max_length=40)
    default_value: str = ""
    privacy_level: str = "normal"
    is_required: bool = False
    is_filterable: bool = False
    sort_order: int = 0
    is_active: bool = True


class AttributeOptionCreate(BaseModel):
    definition_id: int
    label: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=120)
    sort_order: int = 0


class AttributeOptionUpdate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    sort_order: int = 0
    is_active: bool = True


class AttributeOptionResponse(AttributeOptionUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    definition_id: int
    value: str


class AttributeDefinitionResponse(AttributeDefinitionUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    key: str
    options: list[AttributeOptionResponse] = Field(default_factory=list)


class ItemStatusCreate(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    semantic: str = Field(min_length=1, max_length=80)
    sort_order: int = 0


class ItemStatusUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    semantic: str = Field(min_length=1, max_length=80)
    sort_order: int = 0
    is_active: bool = True


class ItemStatusResponse(ItemStatusUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    is_system: bool


class DictionaryGroupCreate(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)


class DictionaryOptionResponse(ResponseModel):
    id: int
    group_id: int
    label: str
    value: str
    sort_order: int
    is_active: bool


class DictionaryGroupResponse(ResponseModel):
    id: int
    code: str
    name: str
    is_system: bool
    is_active: bool
    options: list[DictionaryOptionResponse] = Field(default_factory=list)


class DictionaryOptionCreate(BaseModel):
    group_id: int
    label: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=120)
    sort_order: int = 0


class ConfigBootstrapResponse(BaseModel):
    home_space: HomeSpaceResponse
    residences: list[ResidenceResponse]
    location_tree: list[LocationNodeResponse]
    family_members: list[FamilyMemberResponse]
    categories: list[CategoryResponse]
    item_statuses: list[ItemStatusResponse]
    dictionary_groups: list[DictionaryGroupResponse]
