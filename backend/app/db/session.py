"""Engine, session factory and the FastAPI request-scoped session dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _build_engine() -> Engine:
    if settings.is_sqlite:
        # check_same_thread=False is required because FastAPI serves requests
        # from a thread pool while sharing one SQLite connection pool.
        return create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
    return create_engine(settings.database_url, pool_pre_ping=True, pool_size=10)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """SQLite ignores FK constraints unless they are switched on per connection."""
    if settings.is_sqlite:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
