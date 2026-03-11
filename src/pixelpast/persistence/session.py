"""Database engine and session factory helpers."""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from pixelpast.shared.settings import Settings, get_settings


def create_database_engine(settings: Settings | None = None) -> Engine:
    """Create a SQLAlchemy engine for the configured database backend."""

    runtime_settings = settings or get_settings()
    connect_args = (
        {"check_same_thread": False}
        if runtime_settings.database_url.startswith("sqlite")
        else {}
    )
    return create_engine(
        runtime_settings.database_url,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def create_session_factory(
    settings: Settings | None = None,
) -> sessionmaker[Session]:
    """Create a configured SQLAlchemy session factory."""

    engine = create_database_engine(settings=settings)
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


@contextmanager
def session_scope(
    settings: Settings | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> Generator[Session, None, None]:
    """Provide a transactional session for API and non-API callers."""

    factory = session_factory or create_session_factory(settings=settings)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
