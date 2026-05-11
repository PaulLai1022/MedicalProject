"""SQLAlchemy engine and Session management."""

from collections.abc import Generator
from typing import Any

from sqlalchemy import event, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
    """Enable foreign-key constraints on every SQLite connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """ORM base class."""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a DB Session and close it when the request ends."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
