import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.configuration import (
    AttributeDefinition,
    Category,
    DictionaryGroup,
    HomeSpace,
    ItemStatus,
    Residence,
)
from app.schemas.configuration import (
    AttributeDefinitionCreate,
    CategoryCreate,
    LocationNodeCreate,
    ResidenceCreate,
)
from app.services.configuration import (
    assert_category_parent_valid,
    assert_location_parent_valid,
    create_attribute_definition,
    create_category,
    create_location_node,
    create_residence,
    ensure_core_configuration_seed,
    get_config_bootstrap,
)


def assert_bad_request_message(exc_info: pytest.ExceptionInfo[HTTPException], message: str) -> None:
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == {"message": message}


def test_core_configuration_seed_is_idempotent(db_session: Session) -> None:
    first = ensure_core_configuration_seed(db_session)
    second = ensure_core_configuration_seed(db_session)

    home_spaces = db_session.scalars(select(HomeSpace)).all()
    statuses = db_session.scalars(select(ItemStatus)).all()
    groups = db_session.scalars(select(DictionaryGroup)).all()

    assert first.home_space.id == second.home_space.id
    assert [space.name for space in home_spaces] == ["我们家"]
    assert {status.code for status in statuses} == {
        "in_stock",
        "loaned",
        "discarded",
        "given_away",
        "sold",
        "lost",
        "consumed",
    }
    assert {"units", "importance", "storage_conditions"}.issubset({group.code for group in groups})


def test_core_configuration_seed_reuses_renamed_active_home_space(db_session: Session) -> None:
    first = ensure_core_configuration_seed(db_session)
    first.home_space.name = "新家"
    db_session.commit()

    second = ensure_core_configuration_seed(db_session)
    active_home_spaces = db_session.scalars(select(HomeSpace).where(HomeSpace.is_active.is_(True))).all()

    assert second.home_space.id == first.home_space.id
    assert [space.id for space in active_home_spaces] == [first.home_space.id]


def test_config_bootstrap_does_not_commit_pending_objects(db_session: Session) -> None:
    seed = ensure_core_configuration_seed(db_session)
    db_session.add(Residence(home_space_id=seed.home_space.id, name="未提交住宅"))

    get_config_bootstrap(db_session)
    db_session.rollback()

    saved = db_session.scalar(select(Residence).where(Residence.name == "未提交住宅"))
    assert saved is None


def test_create_residence_rejects_duplicate_name(db_session: Session) -> None:
    payload = ResidenceCreate(name="主住宅")
    create_residence(db_session, payload)

    with pytest.raises(HTTPException) as exc_info:
        create_residence(db_session, payload)

    assert_bad_request_message(exc_info, "住宅名称已存在")


def test_create_residence_rolls_back_commit_time_duplicate_name(db_session: Session) -> None:
    seed = ensure_core_configuration_seed(db_session)
    db_session.add(Residence(home_space_id=seed.home_space.id, name="主住宅"))

    with pytest.raises(HTTPException) as exc_info:
        create_residence(db_session, ResidenceCreate(name="主住宅"))

    assert_bad_request_message(exc_info, "住宅名称已存在")
    assert db_session.scalar(select(HomeSpace).where(HomeSpace.id == seed.home_space.id)) is not None


def test_create_category_rejects_duplicate_code(db_session: Session) -> None:
    payload = CategoryCreate(code="documents", name="证件")
    create_category(db_session, payload)

    with pytest.raises(HTTPException) as exc_info:
        create_category(db_session, CategoryCreate(code="documents", name="其他证件"))

    assert_bad_request_message(exc_info, "分类编码已存在")


def test_create_category_rolls_back_commit_time_duplicate_code(db_session: Session) -> None:
    db_session.add(Category(code="documents", name="证件"))

    with pytest.raises(HTTPException) as exc_info:
        create_category(db_session, CategoryCreate(code="documents", name="其他证件"))

    assert_bad_request_message(exc_info, "分类编码已存在")
    assert db_session.scalars(select(Category)).all() == []


def test_create_attribute_definition_rejects_duplicate_key_in_category(db_session: Session) -> None:
    category = create_category(db_session, CategoryCreate(code="documents", name="证件"))
    payload = AttributeDefinitionCreate(
        category_id=category.id,
        key="expire_date",
        name="有效期",
        field_type="date",
    )
    create_attribute_definition(db_session, payload)

    with pytest.raises(HTTPException) as exc_info:
        create_attribute_definition(
            db_session,
            AttributeDefinitionCreate(
                category_id=category.id,
                key="expire_date",
                name="到期日",
                field_type="date",
            ),
        )

    assert_bad_request_message(exc_info, "字段标识已存在")


def test_create_attribute_definition_rolls_back_commit_time_duplicate_key(db_session: Session) -> None:
    category = create_category(db_session, CategoryCreate(code="documents", name="证件"))
    db_session.add(
        AttributeDefinition(
            category_id=category.id,
            key="expire_date",
            name="有效期",
            field_type="date",
            is_active=True,
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        create_attribute_definition(
            db_session,
            AttributeDefinitionCreate(
                category_id=category.id,
                key="expire_date",
                name="到期日",
                field_type="date",
            ),
        )

    assert_bad_request_message(exc_info, "字段标识已存在")
    assert db_session.scalar(select(Category).where(Category.id == category.id)) is not None


def test_location_parent_validation_rejects_missing_different_residence_and_self(db_session: Session) -> None:
    first_residence = create_residence(db_session, ResidenceCreate(name="住宅一"))
    second_residence = create_residence(db_session, ResidenceCreate(name="住宅二"))
    first_node = create_location_node(
        db_session,
        LocationNodeCreate(residence_id=first_residence.id, name="客厅"),
    )

    with pytest.raises(HTTPException) as missing_exc:
        create_location_node(
            db_session,
            LocationNodeCreate(residence_id=first_residence.id, parent_id=999, name="柜子"),
        )
    assert_bad_request_message(missing_exc, "位置上级节点不合法")

    with pytest.raises(HTTPException) as different_residence_exc:
        create_location_node(
            db_session,
            LocationNodeCreate(residence_id=second_residence.id, parent_id=first_node.id, name="卧室"),
        )
    assert_bad_request_message(different_residence_exc, "位置上级节点不合法")

    with pytest.raises(HTTPException) as self_exc:
        assert_location_parent_valid(db_session, first_residence.id, first_node.id, current_id=first_node.id)
    assert_bad_request_message(self_exc, "位置上级节点不合法")


def test_location_parent_validation_rejects_descendant_cycle(db_session: Session) -> None:
    residence = create_residence(db_session, ResidenceCreate(name="住宅一"))
    parent = create_location_node(
        db_session,
        LocationNodeCreate(residence_id=residence.id, name="客厅"),
    )
    child = create_location_node(
        db_session,
        LocationNodeCreate(residence_id=residence.id, parent_id=parent.id, name="电视柜"),
    )

    with pytest.raises(HTTPException) as exc_info:
        assert_location_parent_valid(db_session, residence.id, child.id, current_id=parent.id)

    assert_bad_request_message(exc_info, "位置上级节点不合法")


def test_category_parent_validation_rejects_cycle(db_session: Session) -> None:
    parent = create_category(db_session, CategoryCreate(code="parent", name="父分类"))
    child = create_category(db_session, CategoryCreate(parent_id=parent.id, code="child", name="子分类"))

    with pytest.raises(HTTPException) as exc_info:
        assert_category_parent_valid(db_session, child.id, current_id=parent.id)

    assert_bad_request_message(exc_info, "分类上级节点不合法")
