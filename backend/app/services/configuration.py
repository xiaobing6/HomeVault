from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import bad_request
from app.models.configuration import (
    AttributeDefinition,
    Category,
    DictionaryGroup,
    FamilyMember,
    HomeSpace,
    ItemStatus,
    LocationNode,
    Residence,
)
from app.schemas.configuration import (
    AttributeDefinitionCreate,
    AttributeDefinitionResponse,
    CategoryCreate,
    CategoryResponse,
    ConfigBootstrapResponse,
    DictionaryGroupResponse,
    FamilyMemberCreate,
    FamilyMemberResponse,
    HomeSpaceResponse,
    ItemStatusResponse,
    LocationNodeCreate,
    LocationNodeResponse,
    ResidenceCreate,
    ResidenceResponse,
)

HOME_SPACE_NAME = "我们家"

CORE_ITEM_STATUSES = [
    ("in_stock", "在库", "available", 10),
    ("loaned", "借出", "away", 20),
    ("discarded", "已丢弃", "removed", 30),
    ("given_away", "已赠送", "removed", 40),
    ("sold", "已出售", "removed", 50),
    ("lost", "遗失", "missing", 60),
    ("consumed", "已耗尽", "removed", 70),
]

CORE_DICTIONARY_GROUPS = [
    ("units", "单位"),
    ("importance", "重要程度"),
    ("storage_conditions", "存放条件"),
]


def commit_or_bad_request(db: Session, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise bad_request(message) from exc


@dataclass(frozen=True)
class CoreConfigurationSeedResult:
    home_space: HomeSpace
    item_statuses: list[ItemStatus]
    dictionary_groups: list[DictionaryGroup]


def ensure_core_configuration_seed(db: Session) -> CoreConfigurationSeedResult:
    home_space = get_or_create_home_space(db)

    for code, name, semantic, sort_order in CORE_ITEM_STATUSES:
        status = db.scalar(select(ItemStatus).where(ItemStatus.code == code))
        if status is None:
            db.add(
                ItemStatus(
                    code=code,
                    name=name,
                    semantic=semantic,
                    sort_order=sort_order,
                    is_system=True,
                    is_active=True,
                )
            )

    for code, name in CORE_DICTIONARY_GROUPS:
        group = db.scalar(select(DictionaryGroup).where(DictionaryGroup.code == code))
        if group is None:
            db.add(DictionaryGroup(code=code, name=name, is_system=True, is_active=True))

    db.commit()
    db.refresh(home_space)

    item_statuses = db.scalars(
        select(ItemStatus)
        .where(ItemStatus.code.in_([code for code, _name, _semantic, _sort_order in CORE_ITEM_STATUSES]))
        .order_by(ItemStatus.sort_order, ItemStatus.id)
    ).all()
    dictionary_groups = db.scalars(
        select(DictionaryGroup)
        .where(DictionaryGroup.code.in_([code for code, _name in CORE_DICTIONARY_GROUPS]))
        .options(selectinload(DictionaryGroup.options))
        .order_by(DictionaryGroup.code)
    ).all()

    return CoreConfigurationSeedResult(
        home_space=home_space,
        item_statuses=list(item_statuses),
        dictionary_groups=list(dictionary_groups),
    )


def get_or_create_home_space(db: Session) -> HomeSpace:
    home_space = db.scalar(
        select(HomeSpace)
        .where(HomeSpace.is_active.is_(True))
        .order_by(HomeSpace.id)
    )
    if home_space is not None:
        return home_space

    home_space = db.scalar(select(HomeSpace).where(HomeSpace.name == HOME_SPACE_NAME))
    if home_space is None:
        home_space = HomeSpace(
            name=HOME_SPACE_NAME,
            description="",
            is_active=True,
        )
        db.add(home_space)
        db.flush()
    else:
        home_space.is_active = True
    return home_space


def list_residences(db: Session) -> list[Residence]:
    return list(
        db.scalars(
            select(Residence)
            .options(selectinload(Residence.location_nodes))
            .order_by(Residence.sort_order, Residence.id)
        ).all()
    )


def build_location_tree(nodes: list[LocationNode]) -> list[LocationNodeResponse]:
    children_by_parent: dict[int | None, list[LocationNode]] = {}
    node_ids = {node.id for node in nodes}
    for node in sorted(nodes, key=lambda item: (item.sort_order, item.id)):
        parent_id = node.parent_id if node.parent_id in node_ids else None
        children_by_parent.setdefault(parent_id, []).append(node)

    def build(node: LocationNode) -> LocationNodeResponse:
        return LocationNodeResponse(
            id=node.id,
            residence_id=node.residence_id,
            parent_id=node.parent_id,
            name=node.name,
            node_type=node.node_type,
            icon=node.icon,
            sort_order=node.sort_order,
            note=node.note,
            is_active=node.is_active,
            children=[build(child) for child in children_by_parent.get(node.id, [])],
        )

    return [build(node) for node in children_by_parent.get(None, [])]


def build_category_tree(categories: list[Category]) -> list[CategoryResponse]:
    children_by_parent: dict[int | None, list[Category]] = {}
    category_ids = {category.id for category in categories}
    for category in sorted(categories, key=lambda item: (item.sort_order, item.name, item.id)):
        parent_id = category.parent_id if category.parent_id in category_ids else None
        children_by_parent.setdefault(parent_id, []).append(category)

    def build(category: Category) -> CategoryResponse:
        return CategoryResponse(
            id=category.id,
            parent_id=category.parent_id,
            code=category.code,
            name=category.name,
            icon=category.icon,
            sort_order=category.sort_order,
            is_active=category.is_active,
            children=[build(child) for child in children_by_parent.get(category.id, [])],
        )

    return [build(category) for category in children_by_parent.get(None, [])]


def assert_location_parent_valid(
    db: Session,
    residence_id: int,
    parent_id: int | None,
    current_id: int | None = None,
) -> None:
    if parent_id is None:
        return
    if current_id is not None and parent_id == current_id:
        raise bad_request("位置上级节点不合法")

    parent = db.get(LocationNode, parent_id)
    if parent is None or parent.residence_id != residence_id:
        raise bad_request("位置上级节点不合法")

    visited: set[int] = set()
    next_parent: LocationNode | None = parent
    while next_parent is not None:
        if current_id is not None and next_parent.id == current_id:
            raise bad_request("位置上级节点不合法")
        if next_parent.id in visited:
            raise bad_request("位置上级节点不合法")
        visited.add(next_parent.id)

        if next_parent.parent_id is None:
            return
        next_parent = db.get(LocationNode, next_parent.parent_id)
        if next_parent is None or next_parent.residence_id != residence_id:
            raise bad_request("位置上级节点不合法")


def assert_category_parent_valid(
    db: Session,
    parent_id: int | None,
    current_id: int | None = None,
) -> None:
    if parent_id is None:
        return
    if current_id is not None and parent_id == current_id:
        raise bad_request("分类上级节点不合法")

    parent = db.get(Category, parent_id)
    if parent is None:
        raise bad_request("分类上级节点不合法")

    visited: set[int] = set()
    next_parent_id = parent.parent_id
    while next_parent_id is not None:
        if current_id is not None and next_parent_id == current_id:
            raise bad_request("分类上级节点不合法")
        if next_parent_id in visited:
            raise bad_request("分类上级节点不合法")
        visited.add(next_parent_id)
        next_parent = db.get(Category, next_parent_id)
        if next_parent is None:
            raise bad_request("分类上级节点不合法")
        next_parent_id = next_parent.parent_id


def get_config_bootstrap(db: Session) -> ConfigBootstrapResponse:
    with db.no_autoflush:
        home_space = db.scalar(
            select(HomeSpace)
            .where(HomeSpace.is_active.is_(True))
            .order_by(HomeSpace.id)
        )
        if home_space is None:
            raise bad_request("核心配置未初始化")

        residences = list_residences(db)
        location_nodes = db.scalars(
            select(LocationNode).order_by(LocationNode.sort_order, LocationNode.id)
        ).all()
        family_members = db.scalars(
            select(FamilyMember).order_by(FamilyMember.id)
        ).all()
        categories = db.scalars(
            select(Category).order_by(Category.sort_order, Category.name, Category.id)
        ).all()
        item_statuses = db.scalars(
            select(ItemStatus).order_by(ItemStatus.sort_order, ItemStatus.id)
        ).all()
        dictionary_groups = db.scalars(
            select(DictionaryGroup)
            .options(selectinload(DictionaryGroup.options))
            .order_by(DictionaryGroup.code)
        ).all()

    return ConfigBootstrapResponse(
        home_space=HomeSpaceResponse.model_validate(home_space),
        residences=[ResidenceResponse.model_validate(residence) for residence in residences],
        location_tree=build_location_tree(list(location_nodes)),
        family_members=[FamilyMemberResponse.model_validate(member) for member in family_members],
        categories=build_category_tree(list(categories)),
        item_statuses=[ItemStatusResponse.model_validate(status) for status in item_statuses],
        dictionary_groups=[
            DictionaryGroupResponse.model_validate(group)
            for group in dictionary_groups
        ],
    )


def create_residence(db: Session, payload: ResidenceCreate) -> ResidenceResponse:
    home_space = get_or_create_home_space(db)
    existing = db.scalar(select(Residence).where(Residence.name == payload.name))
    if existing is not None:
        raise bad_request("住宅名称已存在")

    residence = Residence(
        home_space_id=home_space.id,
        name=payload.name,
        description=payload.description,
        address=payload.address,
        sort_order=payload.sort_order,
        is_active=True,
    )
    db.add(residence)
    commit_or_bad_request(db, "住宅名称已存在")
    db.refresh(residence)
    return ResidenceResponse.model_validate(residence)


def create_location_node(db: Session, payload: LocationNodeCreate) -> LocationNodeResponse:
    residence = db.get(Residence, payload.residence_id)
    if residence is None:
        raise bad_request("住宅不存在")
    assert_location_parent_valid(db, payload.residence_id, payload.parent_id)

    node = LocationNode(
        residence_id=payload.residence_id,
        parent_id=payload.parent_id,
        name=payload.name,
        node_type=payload.node_type,
        icon=payload.icon,
        sort_order=payload.sort_order,
        note=payload.note,
        is_active=True,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return LocationNodeResponse.model_validate(node)


def create_family_member(db: Session, payload: FamilyMemberCreate) -> FamilyMemberResponse:
    home_space = get_or_create_home_space(db)
    member = FamilyMember(
        home_space_id=home_space.id,
        name=payload.name,
        relation=payload.relation,
        phone=payload.phone,
        note=payload.note,
        is_active=True,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return FamilyMemberResponse.model_validate(member)


def create_category(db: Session, payload: CategoryCreate) -> CategoryResponse:
    existing = db.scalar(select(Category).where(Category.code == payload.code))
    if existing is not None:
        raise bad_request("分类编码已存在")

    assert_category_parent_valid(db, payload.parent_id)
    category = Category(
        parent_id=payload.parent_id,
        code=payload.code,
        name=payload.name,
        icon=payload.icon,
        sort_order=payload.sort_order,
        is_active=True,
    )
    db.add(category)
    commit_or_bad_request(db, "分类编码已存在")
    db.refresh(category)
    return CategoryResponse.model_validate(category)


def create_attribute_definition(
    db: Session,
    payload: AttributeDefinitionCreate,
) -> AttributeDefinitionResponse:
    category = db.get(Category, payload.category_id)
    if category is None:
        raise bad_request("分类不存在")

    existing = db.scalar(
        select(AttributeDefinition).where(
            AttributeDefinition.category_id == payload.category_id,
            AttributeDefinition.key == payload.key,
        )
    )
    if existing is not None:
        raise bad_request("字段标识已存在")

    definition = AttributeDefinition(
        category_id=payload.category_id,
        key=payload.key,
        name=payload.name,
        field_type=payload.field_type,
        default_value=payload.default_value,
        privacy_level=payload.privacy_level,
        is_required=payload.is_required,
        is_filterable=payload.is_filterable,
        sort_order=payload.sort_order,
        is_active=True,
    )
    db.add(definition)
    commit_or_bad_request(db, "字段标识已存在")
    db.refresh(definition)
    return AttributeDefinitionResponse.model_validate(definition)
