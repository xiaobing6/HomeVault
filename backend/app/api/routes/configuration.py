from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.auth import User
from app.schemas.configuration import (
    AttributeDefinitionCreate,
    AttributeDefinitionResponse,
    CategoryCreate,
    CategoryResponse,
    ConfigBootstrapResponse,
    DictionaryGroupResponse,
    FamilyMemberCreate,
    FamilyMemberResponse,
    ItemStatusResponse,
    LocationNodeCreate,
    LocationNodeResponse,
    ResidenceCreate,
    ResidenceResponse,
)
from app.services.configuration import (
    create_attribute_definition as create_attribute_definition_record,
    create_category as create_category_record,
    create_family_member as create_family_member_record,
    create_location_node as create_location_node_record,
    create_residence as create_residence_record,
    get_config_bootstrap,
    list_category_tree,
    list_dictionary_groups,
    list_family_members,
    list_item_statuses,
    list_location_tree,
    list_residences,
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


@router.post("/residences", response_model=ResidenceResponse, status_code=status.HTTP_201_CREATED)
def create_residence(
    payload: ResidenceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> ResidenceResponse:
    return create_residence_record(db, payload)


@router.post("/location-nodes", response_model=LocationNodeResponse, status_code=status.HTTP_201_CREATED)
def create_location_node(
    payload: LocationNodeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> LocationNodeResponse:
    return create_location_node_record(db, payload)


@router.post("/family-members", response_model=FamilyMemberResponse, status_code=status.HTTP_201_CREATED)
def create_family_member(
    payload: FamilyMemberCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> FamilyMemberResponse:
    return create_family_member_record(db, payload)


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> CategoryResponse:
    return create_category_record(db, payload)


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
