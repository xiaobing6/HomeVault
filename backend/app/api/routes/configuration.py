from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.auth import User
from app.schemas.configuration import (
    AttributeDefinitionCreate,
    AttributeDefinitionResponse,
    AttributeDefinitionUpdate,
    AttributeOptionCreate,
    AttributeOptionResponse,
    AttributeOptionUpdate,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    ConfigBootstrapResponse,
    DictionaryGroupCreate,
    DictionaryGroupResponse,
    DictionaryOptionCreate,
    DictionaryOptionResponse,
    FamilyMemberCreate,
    FamilyMemberResponse,
    FamilyMemberUpdate,
    HomeSpaceResponse,
    HomeSpaceUpdate,
    ItemStatusCreate,
    ItemStatusResponse,
    ItemStatusUpdate,
    LocationNodeCreate,
    LocationNodeResponse,
    LocationNodeUpdate,
    ResidenceCreate,
    ResidenceResponse,
    ResidenceUpdate,
)
from app.services.configuration import (
    create_attribute_option as create_attribute_option_record,
    create_attribute_definition as create_attribute_definition_record,
    create_category as create_category_record,
    create_dictionary_group as create_dictionary_group_record,
    create_dictionary_option as create_dictionary_option_record,
    create_family_member as create_family_member_record,
    create_item_status as create_item_status_record,
    create_location_node as create_location_node_record,
    create_residence as create_residence_record,
    get_config_bootstrap,
    list_category_tree,
    list_dictionary_groups,
    list_family_members,
    list_item_statuses,
    list_location_tree,
    list_residences,
    update_attribute_definition as update_attribute_definition_record,
    update_attribute_option as update_attribute_option_record,
    update_category as update_category_record,
    update_family_member as update_family_member_record,
    update_home_space as update_home_space_record,
    update_item_status as update_item_status_record,
    update_location_node as update_location_node_record,
    update_residence as update_residence_record,
)

router = APIRouter(prefix="/config", tags=["configuration"])


@router.get("/bootstrap", response_model=ConfigBootstrapResponse)
def bootstrap(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("items:view")),
) -> ConfigBootstrapResponse:
    return get_config_bootstrap(db)


@router.get("/residences", response_model=list[ResidenceResponse])
def residences(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("items:view")),
) -> list[ResidenceResponse]:
    return [ResidenceResponse.model_validate(residence) for residence in list_residences(db)]


@router.get("/location-tree", response_model=list[LocationNodeResponse])
def location_tree(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("items:view")),
) -> list[LocationNodeResponse]:
    return list_location_tree(db)


@router.get("/family-members", response_model=list[FamilyMemberResponse])
def family_members(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("items:view")),
) -> list[FamilyMemberResponse]:
    return list_family_members(db)


@router.get("/categories", response_model=list[CategoryResponse])
def categories(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("items:view")),
) -> list[CategoryResponse]:
    return list_category_tree(db)


@router.get("/item-statuses", response_model=list[ItemStatusResponse])
def item_statuses(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("items:view")),
) -> list[ItemStatusResponse]:
    return list_item_statuses(db)


@router.get("/dictionary-groups", response_model=list[DictionaryGroupResponse])
def dictionary_groups(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("items:view")),
) -> list[DictionaryGroupResponse]:
    return list_dictionary_groups(db)


@router.get("/dictionaries", response_model=list[DictionaryGroupResponse])
def dictionaries(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("items:view")),
) -> list[DictionaryGroupResponse]:
    return list_dictionary_groups(db)


@router.put("/home-space", response_model=HomeSpaceResponse)
def update_home_space(
    payload: HomeSpaceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> HomeSpaceResponse:
    return update_home_space_record(db, payload)


@router.post("/residences", response_model=ResidenceResponse, status_code=status.HTTP_201_CREATED)
def create_residence(
    payload: ResidenceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> ResidenceResponse:
    return create_residence_record(db, payload)


@router.patch("/residences/{residence_id}", response_model=ResidenceResponse)
def update_residence(
    residence_id: int,
    payload: ResidenceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> ResidenceResponse:
    return update_residence_record(db, residence_id, payload)


@router.post("/location-nodes", response_model=LocationNodeResponse, status_code=status.HTTP_201_CREATED)
def create_location_node(
    payload: LocationNodeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> LocationNodeResponse:
    return create_location_node_record(db, payload)


@router.patch("/location-nodes/{node_id}", response_model=LocationNodeResponse)
def update_location_node(
    node_id: int,
    payload: LocationNodeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> LocationNodeResponse:
    return update_location_node_record(db, node_id, payload)


@router.post("/family-members", response_model=FamilyMemberResponse, status_code=status.HTTP_201_CREATED)
def create_family_member(
    payload: FamilyMemberCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> FamilyMemberResponse:
    return create_family_member_record(db, payload)


@router.patch("/family-members/{member_id}", response_model=FamilyMemberResponse)
def update_family_member(
    member_id: int,
    payload: FamilyMemberUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> FamilyMemberResponse:
    return update_family_member_record(db, member_id, payload)


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> CategoryResponse:
    return create_category_record(db, payload)


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> CategoryResponse:
    return update_category_record(db, category_id, payload)


@router.post(
    "/attribute-definitions",
    response_model=AttributeDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_attribute_definition(
    payload: AttributeDefinitionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> AttributeDefinitionResponse:
    return create_attribute_definition_record(db, payload)


@router.patch("/attribute-definitions/{definition_id}", response_model=AttributeDefinitionResponse)
def update_attribute_definition(
    definition_id: int,
    payload: AttributeDefinitionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> AttributeDefinitionResponse:
    return update_attribute_definition_record(db, definition_id, payload)


@router.post(
    "/attribute-options",
    response_model=AttributeOptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_attribute_option(
    payload: AttributeOptionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> AttributeOptionResponse:
    return create_attribute_option_record(db, payload)


@router.patch("/attribute-options/{option_id}", response_model=AttributeOptionResponse)
def update_attribute_option(
    option_id: int,
    payload: AttributeOptionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> AttributeOptionResponse:
    return update_attribute_option_record(db, option_id, payload)


@router.post("/item-statuses", response_model=ItemStatusResponse, status_code=status.HTTP_201_CREATED)
def create_item_status(
    payload: ItemStatusCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> ItemStatusResponse:
    return create_item_status_record(db, payload)


@router.patch("/item-statuses/{status_id}", response_model=ItemStatusResponse)
def update_item_status(
    status_id: int,
    payload: ItemStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> ItemStatusResponse:
    return update_item_status_record(db, status_id, payload)


@router.post("/dictionary-groups", response_model=DictionaryGroupResponse, status_code=status.HTTP_201_CREATED)
def create_dictionary_group(
    payload: DictionaryGroupCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> DictionaryGroupResponse:
    return create_dictionary_group_record(db, payload)


@router.post("/dictionary-options", response_model=DictionaryOptionResponse, status_code=status.HTTP_201_CREATED)
def create_dictionary_option(
    payload: DictionaryOptionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> DictionaryOptionResponse:
    return create_dictionary_option_record(db, payload)
