from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


def _connect_args(database_url: str) -> dict[str, bool]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def create_db_engine(database_url: str) -> Engine:
    engine_options = {
        "connect_args": _connect_args(database_url),
        "future": True,
    }
    if database_url == "sqlite:///:memory:":
        engine_options["poolclass"] = StaticPool

    db_engine = create_engine(
        database_url,
        **engine_options,
    )
    if database_url.startswith("sqlite"):
        event.listen(db_engine, "connect", _enable_sqlite_foreign_keys)
    return db_engine


settings = get_settings()
engine = create_db_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
