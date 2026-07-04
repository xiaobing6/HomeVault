from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import bad_request, not_found
from app.models.auth import User
from app.models.configuration import (
    AttributeDefinition,
    AttributeOption,
    Category,
    DictionaryGroup,
    DictionaryOption,
    FamilyMember,
    HomeSpace,
    ItemStatus,
    LocationNode,
    Residence,
    utcnow,
)
from app.models.inventory import Item
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
    DictionaryGroupResponse,
    DictionaryOptionResponse,
    DictionaryOptionUpdate,
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
from app.services.audit import record_audit_log
from app.services.dictionaries import require_active_dictionary_value
from app.services.privacy import normalize_privacy_level
from app.services.uploads import (
    IMAGE_CONTENT_TYPES,
    delete_stored_upload,
    protected_residence_image_url,
    store_upload,
    stored_upload_path,
    validate_image_signature,
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
    (
        "units",
        "\u5355\u4f4d",
        [
            ("\u4ef6", "\u4ef6", 10),
            ("\u4e2a", "\u4e2a", 20),
            ("\u7bb1", "\u7bb1", 30),
            ("\u5957", "\u5957", 40),
        ],
    ),
    (
        "importance",
        "\u91cd\u8981\u7a0b\u5ea6",
        [
            ("high", "\u9ad8", 10),
            ("medium", "\u4e2d", 20),
            ("low", "\u4f4e", 30),
        ],
    ),
    (
        "location_node_types",
        "\u4f4d\u7f6e\u7c7b\u578b",
        [
            ("room", "\u623f\u95f4", 10),
            ("area", "\u533a\u57df", 20),
            ("cabinet", "\u67dc\u5b50", 30),
            ("shelf", "\u67b6\u5b50", 40),
            ("box", "\u7bb1/\u76d2", 50),
            ("other", "\u5176\u4ed6", 60),
        ],
    ),
]

ACTIVE_RESIDENCE_NAME_EXISTS_MESSAGE = "\u542f\u7528\u4f4f\u5b85\u540d\u79f0\u5df2\u5b58\u5728"
LOCATION_NODE_TYPE_GROUP = "location_node_types"
LOCATION_NODE_TYPE_INVALID_MESSAGE = "\u4f4d\u7f6e\u7c7b\u578b\u4e0d\u5408\u6cd5"
RESOURCE_NOT_FOUND_MESSAGE = "\u8d44\u6e90\u4e0d\u5b58\u5728"
LOCATION_DELETE_BLOCKED_BY_ITEMS_MESSAGE = "\u5f53\u524d\u4f4d\u7f6e\u4e0b\u8fd8\u6709\u7269\u54c1\uff0c\u8bf7\u5148\u79fb\u52a8\u6216\u5220\u9664\u7269\u54c1"
RESIDENCE_DELETE_BLOCKED_BY_ITEMS_MESSAGE = "\u5f53\u524d\u4f4f\u5b85\u4e0b\u8fd8\u6709\u7269\u54c1\uff0c\u8bf7\u5148\u79fb\u52a8\u6216\u5220\u9664\u7269\u54c1"


def commit_or_bad_request(db: Session, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise bad_request(message) from exc


def flush_or_bad_request(db: Session, message: str) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise bad_request(message) from exc


@dataclass(frozen=True)
class CoreConfigurationSeedResult:
    home_space: HomeSpace
    item_statuses: list[ItemStatus]
    dictionary_groups: list[DictionaryGroup]


@dataclass(frozen=True)
class MediaFile:
    path: Path
    filename: str
    content_type: str


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

    storage_group = db.scalar(
        select(DictionaryGroup).where(
            DictionaryGroup.code == "storage_conditions",
            DictionaryGroup.is_system.is_(True),
        )
    )
    if storage_group is not None:
        db.delete(storage_group)

    for code, name, options in CORE_DICTIONARY_GROUPS:
        group = db.scalar(select(DictionaryGroup).where(DictionaryGroup.code == code))
        if group is None:
            group = DictionaryGroup(code=code, name=name, is_system=True, is_active=True)
            db.add(group)
            db.flush()
        else:
            group.name = name
            group.is_system = True
            group.is_active = True

        existing_options = {
            option.value: option
            for option in db.scalars(select(DictionaryOption).where(DictionaryOption.group_id == group.id)).all()
        }
        for value, label, sort_order in options:
            if value not in existing_options:
                db.add(
                    DictionaryOption(
                        group_id=group.id,
                        label=label,
                        value=value,
                        sort_order=sort_order,
                        is_active=True,
                    )
                )

    db.commit()
    db.refresh(home_space)

    item_statuses = db.scalars(
        select(ItemStatus)
        .where(ItemStatus.code.in_([code for code, _name, _semantic, _sort_order in CORE_ITEM_STATUSES]))
        .order_by(ItemStatus.sort_order, ItemStatus.id)
    ).all()
    dictionary_groups = db.scalars(
        select(DictionaryGroup)
        .where(DictionaryGroup.code.in_([code for code, _name, _options in CORE_DICTIONARY_GROUPS]))
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
            .where(Residence.is_deleted.is_(False))
            .options(
                selectinload(Residence.location_nodes),
                selectinload(Residence.created_by),
                selectinload(Residence.updated_by),
            )
            .order_by(Residence.updated_at.desc(), Residence.id.desc())
        ).all()
    )


def user_display_name(user: object | None) -> str | None:
    if user is None:
        return None
    display_name = getattr(user, "display_name", "")
    username = getattr(user, "username", "")
    return display_name or username or None


def build_residence_response(residence: Residence) -> ResidenceResponse:
    return ResidenceResponse(
        id=residence.id,
        name=residence.name,
        description=residence.description,
        address=residence.address,
        is_active=residence.is_active,
        is_deleted=residence.is_deleted,
        created_at=residence.created_at,
        updated_at=residence.updated_at,
        created_by_id=residence.created_by_id,
        created_by_name=user_display_name(residence.created_by),
        updated_by_id=residence.updated_by_id,
        updated_by_name=user_display_name(residence.updated_by),
        image_url=protected_residence_image_url(residence.id) if residence.image_path else None,
        image_original_filename=residence.image_original_filename or None,
    )


def list_location_tree(db: Session) -> list[LocationNodeResponse]:
    nodes = db.scalars(
        select(LocationNode)
        .where(LocationNode.is_deleted.is_(False))
        .order_by(LocationNode.sort_order, LocationNode.id)
    ).all()
    return build_location_tree(list(nodes))


def list_family_members(db: Session) -> list[FamilyMemberResponse]:
    members = db.scalars(
        select(FamilyMember)
        .where(FamilyMember.is_deleted.is_(False))
        .order_by(FamilyMember.id)
    ).all()
    return [FamilyMemberResponse.model_validate(member) for member in members]


def list_category_tree(db: Session) -> list[CategoryResponse]:
    categories = db.scalars(
        select(Category)
        .options(selectinload(Category.attribute_definitions).selectinload(AttributeDefinition.options))
        .order_by(Category.sort_order, Category.name, Category.id)
    ).all()
    return build_category_tree(list(categories))


def list_item_statuses(db: Session) -> list[ItemStatusResponse]:
    statuses = db.scalars(
        select(ItemStatus).order_by(ItemStatus.sort_order, ItemStatus.id)
    ).all()
    return [ItemStatusResponse.model_validate(status) for status in statuses]


def list_dictionary_groups(db: Session) -> list[DictionaryGroupResponse]:
    groups = db.scalars(
        select(DictionaryGroup)
        .options(selectinload(DictionaryGroup.options))
        .order_by(DictionaryGroup.code)
    ).all()
    return [DictionaryGroupResponse.model_validate(group) for group in groups]


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
            is_deleted=node.is_deleted,
            children=[build(child) for child in children_by_parent.get(node.id, [])],
        )

    return [build(node) for node in children_by_parent.get(None, [])]


def build_attribute_definition_response(definition: AttributeDefinition) -> AttributeDefinitionResponse:
    return AttributeDefinitionResponse(
        id=definition.id,
        category_id=definition.category_id,
        key=definition.key,
        name=definition.name,
        field_type=definition.field_type,
        default_value=definition.default_value,
        privacy_level=normalize_privacy_level(definition.privacy_level),
        is_required=definition.is_required,
        is_filterable=definition.is_filterable,
        sort_order=definition.sort_order,
        is_active=definition.is_active,
        options=[
            AttributeOptionResponse.model_validate(option)
            for option in sorted(definition.options, key=lambda item: (item.sort_order, item.id))
        ],
    )


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
            attribute_definitions=[
                build_attribute_definition_response(definition)
                for definition in sorted(
                    category.attribute_definitions,
                    key=lambda item: (item.sort_order, item.id),
                )
            ],
            children=[build(child) for child in children_by_parent.get(category.id, [])],
        )

    return [build(category) for category in children_by_parent.get(None, [])]


def collect_location_subtree_ids(nodes: list[LocationNode], root_id: int) -> set[int]:
    children_by_parent: dict[int | None, list[LocationNode]] = {}
    for node in nodes:
        children_by_parent.setdefault(node.parent_id, []).append(node)

    collected: set[int] = set()
    stack = [root_id]
    while stack:
        node_id = stack.pop()
        if node_id in collected:
            continue
        collected.add(node_id)
        stack.extend(child.id for child in children_by_parent.get(node_id, []))
    return collected


def active_inventory_effective_location_ids(db: Session) -> set[int]:
    items = db.scalars(
        select(Item).where(
            Item.is_deleted.is_(False),
            Item.is_archived.is_(False),
        )
    ).all()
    items_by_id = {item.id: item for item in items}
    location_ids: set[int] = set()

    for item in items:
        current: Item | None = item
        visited: set[int] = set()
        while current is not None and current.id not in visited:
            visited.add(current.id)
            if current.location_node_id is not None:
                location_ids.add(current.location_node_id)
                break
            if current.container_item_id is None:
                break
            current = items_by_id.get(current.container_item_id)

    return location_ids


def assert_no_active_items_in_locations(
    db: Session,
    location_ids: set[int],
    message: str,
) -> None:
    if location_ids and active_inventory_effective_location_ids(db).intersection(location_ids):
        raise bad_request(message)


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
    if parent is None or parent.is_deleted or parent.residence_id != residence_id:
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
        if next_parent is None or next_parent.is_deleted or next_parent.residence_id != residence_id:
            raise bad_request("位置上级节点不合法")


def assert_active_residence_name_available(
    db: Session,
    name: str,
    current_id: int | None = None,
) -> None:
    statement = select(Residence).where(
        Residence.name == name,
        Residence.is_active.is_(True),
        Residence.is_deleted.is_(False),
    )
    if current_id is not None:
        statement = statement.where(Residence.id != current_id)

    existing = db.scalar(statement)
    if existing is not None:
        raise bad_request(ACTIVE_RESIDENCE_NAME_EXISTS_MESSAGE)


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
            select(LocationNode)
            .where(LocationNode.is_deleted.is_(False))
            .order_by(LocationNode.sort_order, LocationNode.id)
        ).all()
        family_members = db.scalars(
            select(FamilyMember)
            .where(FamilyMember.is_deleted.is_(False))
            .order_by(FamilyMember.id)
        ).all()
        categories = db.scalars(
            select(Category)
            .options(selectinload(Category.attribute_definitions).selectinload(AttributeDefinition.options))
            .order_by(Category.sort_order, Category.name, Category.id)
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
        residences=[build_residence_response(residence) for residence in residences],
        location_tree=build_location_tree(list(location_nodes)),
        family_members=[FamilyMemberResponse.model_validate(member) for member in family_members],
        categories=build_category_tree(list(categories)),
        item_statuses=[ItemStatusResponse.model_validate(status) for status in item_statuses],
        dictionary_groups=[
            DictionaryGroupResponse.model_validate(group)
            for group in dictionary_groups
        ],
    )


def create_residence(
    db: Session,
    payload: ResidenceCreate,
    actor: User | None = None,
) -> ResidenceResponse:
    seed = ensure_core_configuration_seed(db)
    assert_active_residence_name_available(db, payload.name)

    residence = Residence(
        home_space_id=seed.home_space.id,
        name=payload.name,
        description=payload.description,
        address=payload.address,
        created_by_id=actor.id if actor is not None else None,
        updated_by_id=actor.id if actor is not None else None,
        is_active=True,
    )
    db.add(residence)
    flush_or_bad_request(db, ACTIVE_RESIDENCE_NAME_EXISTS_MESSAGE)
    record_audit_log(
        db,
        action="config.residence.create",
        resource_type="residence",
        actor=actor,
        resource_id=residence.id,
        resource_label=residence.name,
        metadata={"is_active": residence.is_active},
    )
    commit_or_bad_request(db, ACTIVE_RESIDENCE_NAME_EXISTS_MESSAGE)
    db.refresh(residence)
    return build_residence_response(residence)


def create_location_node(
    db: Session,
    payload: LocationNodeCreate,
    actor: User | None = None,
) -> LocationNodeResponse:
    residence = db.get(Residence, payload.residence_id)
    if residence is None or residence.is_deleted:
        raise bad_request("住宅不存在")
    assert_location_parent_valid(db, payload.residence_id, payload.parent_id)
    node_type = require_active_dictionary_value(
        db,
        LOCATION_NODE_TYPE_GROUP,
        payload.node_type,
        message=LOCATION_NODE_TYPE_INVALID_MESSAGE,
    )

    node = LocationNode(
        residence_id=payload.residence_id,
        parent_id=payload.parent_id,
        name=payload.name,
        node_type=node_type,
        icon=payload.icon,
        sort_order=payload.sort_order,
        note=payload.note,
        is_active=True,
    )
    db.add(node)
    db.flush()
    record_audit_log(
        db,
        action="config.location.create",
        resource_type="location_node",
        actor=actor,
        resource_id=node.id,
        resource_label=node.name,
        metadata={"residence_id": node.residence_id},
    )
    db.commit()
    db.refresh(node)
    return LocationNodeResponse.model_validate(node)


def create_family_member(
    db: Session,
    payload: FamilyMemberCreate,
    actor: User | None = None,
) -> FamilyMemberResponse:
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
    db.flush()
    record_audit_log(
        db,
        action="config.family_member.create",
        resource_type="family_member",
        actor=actor,
        resource_id=member.id,
        resource_label=member.name,
    )
    db.commit()
    db.refresh(member)
    return FamilyMemberResponse.model_validate(member)


def create_category(
    db: Session,
    payload: CategoryCreate,
    actor: User | None = None,
) -> CategoryResponse:
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
    flush_or_bad_request(db, "分类编码已存在")
    record_audit_log(
        db,
        action="config.category.create",
        resource_type="category",
        actor=actor,
        resource_id=category.id,
        resource_label=category.name,
        metadata={"code": category.code},
    )
    commit_or_bad_request(db, "分类编码已存在")
    db.refresh(category)
    return CategoryResponse.model_validate(category)


def create_attribute_definition(
    db: Session,
    payload: AttributeDefinitionCreate,
    actor: User | None = None,
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
    flush_or_bad_request(db, "字段标识已存在")
    record_audit_log(
        db,
        action="config.attribute_definition.create",
        resource_type="attribute_definition",
        actor=actor,
        resource_id=definition.id,
        resource_label=definition.name,
        metadata={"category_id": definition.category_id, "key": definition.key},
    )
    commit_or_bad_request(db, "字段标识已存在")
    db.refresh(definition)
    return build_attribute_definition_response(definition)


def update_home_space(db: Session, payload: HomeSpaceUpdate) -> HomeSpaceResponse:
    home_space = get_or_create_home_space(db)
    home_space.name = payload.name
    home_space.description = payload.description
    home_space.is_active = True
    commit_or_bad_request(db, "Home space name already exists")
    db.refresh(home_space)
    return HomeSpaceResponse.model_validate(home_space)


def update_residence(
    db: Session,
    residence_id: int,
    payload: ResidenceUpdate,
    actor: User | None = None,
) -> ResidenceResponse:
    residence = db.get(Residence, residence_id)
    if residence is None or residence.is_deleted:
        raise bad_request("Residence not found")

    if payload.is_active:
        assert_active_residence_name_available(db, payload.name, current_id=residence_id)

    residence.name = payload.name
    residence.description = payload.description
    residence.address = payload.address
    residence.updated_by_id = actor.id if actor is not None else None
    residence.is_active = payload.is_active
    record_audit_log(
        db,
        action="config.residence.update",
        resource_type="residence",
        actor=actor,
        resource_id=residence.id,
        resource_label=residence.name,
        metadata={"is_active": residence.is_active},
    )
    commit_or_bad_request(db, ACTIVE_RESIDENCE_NAME_EXISTS_MESSAGE)
    db.refresh(residence)
    return build_residence_response(residence)


def stored_media_file(relative_path: str) -> Path:
    root = stored_upload_path("").resolve()
    path = stored_upload_path(relative_path).resolve()
    if path != root and root not in path.parents:
        raise not_found("\u56fe\u7247\u4e0d\u5b58\u5728")
    if not path.is_file():
        raise not_found("\u56fe\u7247\u4e0d\u5b58\u5728")
    return path


def get_residence_image_file(db: Session, residence_id: int) -> MediaFile:
    residence = db.get(Residence, residence_id)
    if residence is None or residence.is_deleted or not residence.image_path:
        raise not_found("\u56fe\u7247\u4e0d\u5b58\u5728")
    return MediaFile(
        path=stored_media_file(residence.image_path),
        filename=residence.image_original_filename,
        content_type=residence.image_content_type,
    )


async def replace_residence_image(
    db: Session,
    residence_id: int,
    upload: UploadFile,
    actor: User | None = None,
) -> ResidenceResponse:
    residence = db.get(Residence, residence_id)
    if residence is None or residence.is_deleted:
        raise not_found("\u4f4f\u5b85\u4e0d\u5b58\u5728")

    content_type = upload.content_type or ""
    if content_type not in IMAGE_CONTENT_TYPES:
        raise bad_request("\u56fe\u7247\u683c\u5f0f\u4e0d\u652f\u6301")
    await validate_image_signature(upload, content_type)

    old_image_path = residence.image_path
    file_path = ""
    try:
        file_path, byte_size = await store_upload(
            upload,
            item_id=residence.id,
            media_type="images",
            resource_root="residences",
        )
        residence.image_path = file_path
        residence.image_original_filename = upload.filename or ""
        residence.image_content_type = content_type
        residence.image_byte_size = byte_size
        residence.updated_by_id = actor.id if actor is not None else None
        record_audit_log(
            db,
            action="config.residence.image.update",
            resource_type="residence",
            actor=actor,
            resource_id=residence.id,
            resource_label=residence.name,
            metadata={"image_original_filename": residence.image_original_filename},
        )
        commit_or_bad_request(db, "\u56fe\u7247\u4fdd\u5b58\u5931\u8d25")
    except HTTPException:
        if file_path:
            delete_stored_upload(file_path)
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        if file_path:
            delete_stored_upload(file_path)
        raise bad_request("\u56fe\u7247\u4fdd\u5b58\u5931\u8d25") from exc

    if old_image_path and old_image_path != file_path:
        delete_stored_upload(old_image_path)
    db.refresh(residence)
    return build_residence_response(residence)


def update_location_node(
    db: Session,
    node_id: int,
    payload: LocationNodeUpdate,
    actor: User | None = None,
) -> LocationNodeResponse:
    node = db.get(LocationNode, node_id)
    if node is None or node.is_deleted:
        raise bad_request("Location node not found")

    assert_location_parent_valid(db, node.residence_id, payload.parent_id, current_id=node_id)
    node_type = require_active_dictionary_value(
        db,
        LOCATION_NODE_TYPE_GROUP,
        payload.node_type,
        message=LOCATION_NODE_TYPE_INVALID_MESSAGE,
        allow_existing_value=node.node_type,
    )
    changed_fields: list[str] = []
    if node.parent_id != payload.parent_id:
        changed_fields.append("parent_id")
    if node.name != payload.name:
        changed_fields.append("name")
    if node.node_type != node_type:
        changed_fields.append("node_type")
    if node.icon != payload.icon:
        changed_fields.append("icon")
    if node.sort_order != payload.sort_order:
        changed_fields.append("sort_order")
    if node.note != payload.note:
        changed_fields.append("note")
    if node.is_active != payload.is_active:
        changed_fields.append("is_active")

    node.parent_id = payload.parent_id
    node.name = payload.name
    node.node_type = node_type
    node.icon = payload.icon
    node.sort_order = payload.sort_order
    node.note = payload.note
    node.is_active = payload.is_active
    record_audit_log(
        db,
        action="config.location.update",
        resource_type="location_node",
        actor=actor,
        resource_id=node.id,
        resource_label=node.name,
        metadata={
            "residence_id": node.residence_id,
            "changed_fields": changed_fields,
            "is_active": node.is_active,
        },
    )
    db.commit()
    db.refresh(node)
    return LocationNodeResponse.model_validate(node)


def update_family_member(
    db: Session,
    member_id: int,
    payload: FamilyMemberUpdate,
) -> FamilyMemberResponse:
    member = db.get(FamilyMember, member_id)
    if member is None or member.is_deleted:
        raise bad_request("Family member not found")

    member.name = payload.name
    member.relation = payload.relation
    member.phone = payload.phone
    member.note = payload.note
    member.is_active = payload.is_active
    db.commit()
    db.refresh(member)
    return FamilyMemberResponse.model_validate(member)


def delete_family_member(
    db: Session,
    member_id: int,
    actor: User | None = None,
) -> FamilyMemberResponse:
    member = db.get(FamilyMember, member_id)
    if member is None or member.is_deleted:
        raise not_found(RESOURCE_NOT_FOUND_MESSAGE)

    member.is_deleted = True
    member.deleted_at = utcnow()
    member.deleted_by_id = actor.id if actor is not None else None
    record_audit_log(
        db,
        action="config.family_member.delete",
        resource_type="family_member",
        actor=actor,
        resource_id=member.id,
        resource_label=member.name,
    )
    commit_or_bad_request(db, RESOURCE_NOT_FOUND_MESSAGE)
    db.refresh(member)
    return FamilyMemberResponse.model_validate(member)


def delete_location_node(
    db: Session,
    node_id: int,
    actor: User | None = None,
) -> LocationNodeResponse:
    node = db.get(LocationNode, node_id)
    if node is None or node.is_deleted:
        raise not_found(RESOURCE_NOT_FOUND_MESSAGE)

    nodes = db.scalars(
        select(LocationNode)
        .where(
            LocationNode.residence_id == node.residence_id,
            LocationNode.is_deleted.is_(False),
        )
        .order_by(LocationNode.sort_order, LocationNode.id)
    ).all()
    subtree_ids = collect_location_subtree_ids(list(nodes), node.id)
    assert_no_active_items_in_locations(db, subtree_ids, LOCATION_DELETE_BLOCKED_BY_ITEMS_MESSAGE)

    deleted_at = utcnow()
    actor_id = actor.id if actor is not None else None
    for location in nodes:
        if location.id in subtree_ids:
            location.is_deleted = True
            location.deleted_at = deleted_at
            location.deleted_by_id = actor_id

    record_audit_log(
        db,
        action="config.location.delete",
        resource_type="location_node",
        actor=actor,
        resource_id=node.id,
        resource_label=node.name,
        metadata={"residence_id": node.residence_id, "deleted_count": len(subtree_ids)},
    )
    commit_or_bad_request(db, RESOURCE_NOT_FOUND_MESSAGE)
    db.refresh(node)
    return LocationNodeResponse.model_validate(node)


def delete_residence(
    db: Session,
    residence_id: int,
    actor: User | None = None,
) -> ResidenceResponse:
    residence = db.get(Residence, residence_id)
    if residence is None or residence.is_deleted:
        raise not_found(RESOURCE_NOT_FOUND_MESSAGE)

    nodes = db.scalars(
        select(LocationNode)
        .where(
            LocationNode.residence_id == residence.id,
            LocationNode.is_deleted.is_(False),
        )
        .order_by(LocationNode.sort_order, LocationNode.id)
    ).all()
    location_ids = {node.id for node in nodes}
    assert_no_active_items_in_locations(db, location_ids, RESIDENCE_DELETE_BLOCKED_BY_ITEMS_MESSAGE)

    deleted_at = utcnow()
    actor_id = actor.id if actor is not None else None
    residence.is_deleted = True
    residence.deleted_at = deleted_at
    residence.deleted_by_id = actor_id
    for node in nodes:
        node.is_deleted = True
        node.deleted_at = deleted_at
        node.deleted_by_id = actor_id

    record_audit_log(
        db,
        action="config.residence.delete",
        resource_type="residence",
        actor=actor,
        resource_id=residence.id,
        resource_label=residence.name,
        metadata={"deleted_location_count": len(nodes)},
    )
    commit_or_bad_request(db, RESOURCE_NOT_FOUND_MESSAGE)
    db.refresh(residence)
    return build_residence_response(residence)


def update_category(db: Session, category_id: int, payload: CategoryUpdate) -> CategoryResponse:
    category = db.get(Category, category_id)
    if category is None:
        raise bad_request("Category not found")

    assert_category_parent_valid(db, payload.parent_id, current_id=category_id)
    category.parent_id = payload.parent_id
    category.name = payload.name
    category.icon = payload.icon
    category.sort_order = payload.sort_order
    category.is_active = payload.is_active
    db.commit()
    db.refresh(category)
    return CategoryResponse.model_validate(category)


def update_attribute_definition(
    db: Session,
    definition_id: int,
    payload: AttributeDefinitionUpdate,
) -> AttributeDefinitionResponse:
    definition = db.get(AttributeDefinition, definition_id)
    if definition is None:
        raise bad_request("Attribute definition not found")

    definition.name = payload.name
    definition.field_type = payload.field_type
    definition.default_value = payload.default_value
    definition.privacy_level = payload.privacy_level
    definition.is_required = payload.is_required
    definition.is_filterable = payload.is_filterable
    definition.sort_order = payload.sort_order
    definition.is_active = payload.is_active
    db.commit()
    db.refresh(definition)
    return build_attribute_definition_response(definition)


def create_attribute_option(
    db: Session,
    payload: AttributeOptionCreate,
) -> AttributeOptionResponse:
    definition = db.get(AttributeDefinition, payload.definition_id)
    if definition is None:
        raise bad_request("Attribute definition not found")

    existing = db.scalar(
        select(AttributeOption).where(
            AttributeOption.definition_id == payload.definition_id,
            AttributeOption.value == payload.value,
        )
    )
    if existing is not None:
        raise bad_request("Attribute option value already exists")

    option = AttributeOption(
        definition_id=payload.definition_id,
        label=payload.label,
        value=payload.value,
        sort_order=payload.sort_order,
        is_active=True,
    )
    db.add(option)
    commit_or_bad_request(db, "Attribute option value already exists")
    db.refresh(option)
    return AttributeOptionResponse.model_validate(option)


def update_attribute_option(
    db: Session,
    option_id: int,
    payload: AttributeOptionUpdate,
) -> AttributeOptionResponse:
    option = db.get(AttributeOption, option_id)
    if option is None:
        raise bad_request("Attribute option not found")

    option.label = payload.label
    option.sort_order = payload.sort_order
    option.is_active = payload.is_active
    db.commit()
    db.refresh(option)
    return AttributeOptionResponse.model_validate(option)


def create_item_status(db: Session, payload: ItemStatusCreate) -> ItemStatusResponse:
    existing = db.scalar(select(ItemStatus).where(ItemStatus.code == payload.code))
    if existing is not None:
        raise bad_request("Item status code already exists")

    item_status = ItemStatus(
        code=payload.code,
        name=payload.name,
        semantic=payload.semantic,
        sort_order=payload.sort_order,
        is_system=False,
        is_active=True,
    )
    db.add(item_status)
    commit_or_bad_request(db, "Item status code already exists")
    db.refresh(item_status)
    return ItemStatusResponse.model_validate(item_status)


def update_item_status(db: Session, status_id: int, payload: ItemStatusUpdate) -> ItemStatusResponse:
    item_status = db.get(ItemStatus, status_id)
    if item_status is None:
        raise bad_request("Item status not found")

    item_status.name = payload.name
    item_status.semantic = payload.semantic
    item_status.sort_order = payload.sort_order
    item_status.is_active = payload.is_active
    db.commit()
    db.refresh(item_status)
    return ItemStatusResponse.model_validate(item_status)


def update_dictionary_option(
    db: Session,
    option_id: int,
    payload: DictionaryOptionUpdate,
    actor: User | None = None,
) -> DictionaryOptionResponse:
    option = db.get(DictionaryOption, option_id)
    if option is None:
        raise bad_request("Dictionary option not found")

    group = option.group
    changed_fields: list[str] = []
    if option.label != payload.label:
        changed_fields.append("label")
    if option.sort_order != payload.sort_order:
        changed_fields.append("sort_order")
    if option.is_active != payload.is_active:
        changed_fields.append("is_active")

    option.label = payload.label
    option.sort_order = payload.sort_order
    option.is_active = payload.is_active
    record_audit_log(
        db,
        action="config.dictionary_option.update",
        resource_type="dictionary_option",
        actor=actor,
        resource_id=option.id,
        resource_label=option.value,
        metadata={
            "group_code": group.code if group is not None else None,
            "changed_fields": changed_fields,
            "is_active": option.is_active,
        },
    )
    db.commit()
    db.refresh(option)
    return DictionaryOptionResponse.model_validate(option)
