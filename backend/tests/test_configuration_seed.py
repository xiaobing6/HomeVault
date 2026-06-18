from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.configuration import DictionaryGroup, HomeSpace, ItemStatus
from app.services.configuration import ensure_core_configuration_seed


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
