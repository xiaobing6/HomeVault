from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
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
)


def test_configuration_tables_are_registered() -> None:
    table_names = set(Base.metadata.tables)

    assert {
        "home_spaces",
        "residences",
        "location_nodes",
        "family_members",
        "categories",
        "attribute_definitions",
        "attribute_options",
        "item_statuses",
        "dictionary_groups",
        "dictionary_options",
    }.issubset(table_names)


def test_configuration_models_persist_tree_and_fields(db_session: Session) -> None:
    home = HomeSpace(name="我们家", description="家庭物品空间", is_active=True)
    residence = Residence(name="现在住处", home_space=home, description="主住处", is_active=True)
    room = LocationNode(residence=residence, name="客厅", node_type="room", sort_order=10, is_active=True)
    cabinet = LocationNode(
        residence=residence,
        parent=room,
        name="电视柜",
        node_type="cabinet",
        sort_order=20,
        is_active=True,
    )
    member = FamilyMember(home_space=home, name="妈妈", relation="家人", is_active=True)
    category = Category(name="证件", code="documents", sort_order=10, is_active=True)
    field = AttributeDefinition(
        category=category,
        key="expire_date",
        name="有效期",
        field_type="date",
        is_required=False,
        is_filterable=True,
        sort_order=10,
        is_active=True,
    )
    option = AttributeOption(definition=field, label="长期", value="long_term", sort_order=10, is_active=True)
    status = ItemStatus(code="in_stock", name="在库", semantic="in_inventory", sort_order=10, is_system=True, is_active=True)
    group = DictionaryGroup(code="units", name="单位", is_system=True, is_active=True)
    dictionary_option = DictionaryOption(group=group, label="件", value="piece", sort_order=10, is_active=True)
    db_session.add_all([home, member, option, status, dictionary_option])
    db_session.commit()

    saved_residence = db_session.scalar(select(Residence).where(Residence.name == "现在住处"))
    saved_category = db_session.scalar(select(Category).where(Category.code == "documents"))

    assert saved_residence is not None
    assert [node.name for node in saved_residence.location_nodes] == ["客厅", "电视柜"]
    assert cabinet.parent == room
    assert saved_category is not None
    assert saved_category.attribute_definitions[0].options == [option]
