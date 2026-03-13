"""Shared runtime helpers for API and CLI entrypoints."""

from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from pixelpast.persistence.base import Base
from pixelpast.persistence.session import create_database_engine, create_session_factory
from pixelpast.shared.settings import Settings, get_settings


@dataclass(slots=True, frozen=True)
class RuntimeContext:
    """Shared runtime dependencies for operational entrypoints."""

    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]


def create_runtime_context(settings: Settings | None = None) -> RuntimeContext:
    """Create settings, engine and session factory for a process."""

    runtime_settings = settings or get_settings()
    engine = create_database_engine(settings=runtime_settings)
    session_factory = create_session_factory(
        settings=runtime_settings,
        engine=engine,
    )
    return RuntimeContext(
        settings=runtime_settings,
        engine=engine,
        session_factory=session_factory,
    )


def initialize_database(runtime: RuntimeContext) -> None:
    """Ensure the configured database exists and the schema is ready."""

    _ensure_sqlite_database_directory(runtime.settings)
    if _uses_ephemeral_sqlite(database_url=make_url(runtime.settings.database_url)):
        Base.metadata.create_all(runtime.engine)
        return

    _run_alembic_upgrade(database_url=runtime.settings.database_url)


def _ensure_sqlite_database_directory(settings: Settings) -> None:
    """Create the target directory for file-based SQLite databases."""

    url = make_url(settings.database_url)
    if url.drivername != "sqlite" or not url.database:
        return
    if url.database == ":memory:":
        return

    database_path = Path(url.database)
    database_path.parent.mkdir(parents=True, exist_ok=True)


def _uses_ephemeral_sqlite(*, database_url) -> bool:
    """Return whether initialization should use direct metadata creation."""

    return database_url.drivername == "sqlite" and (
        database_url.database in {None, "", ":memory:"}
    )


def _run_alembic_upgrade(*, database_url: str) -> None:
    """Upgrade the configured database to the latest Alembic revision."""

    repository_root = Path(__file__).resolve().parents[3]
    config = Config((repository_root / "alembic.ini").as_posix())
    config.attributes["database_url"] = database_url
    command.upgrade(config, "head")
