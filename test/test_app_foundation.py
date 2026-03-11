"""Runtime foundation smoke tests."""

from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from alembic import command
from pixelpast.api.app import create_app
from pixelpast.persistence.base import Base
from pixelpast.persistence.session import session_scope
from pixelpast.shared.settings import Settings


def test_fastapi_app_exposes_health_endpoint() -> None:
    settings = Settings(database_url="sqlite://")
    app = create_app(settings=settings)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_non_api_session_scope_creates_session() -> None:
    settings = Settings(database_url="sqlite://")

    with session_scope(settings=settings) as session:
        value = session.execute(text("SELECT 1")).scalar_one()

    assert value == 1


def test_session_factory_is_available_on_app_state() -> None:
    settings = Settings(database_url="sqlite://")
    app = create_app(settings=settings)

    with app.state.session_factory() as session:
        value = session.execute(text("SELECT 1")).scalar_one()

    assert value == 1


def test_alembic_upgrade_head_runs() -> None:
    database_dir = Path("var")
    database_dir.mkdir(exist_ok=True)
    database_path = database_dir / f"test-alembic-{uuid4().hex}.db"
    config = Config("alembic.ini")
    config.attributes["database_url"] = f"sqlite:///{database_path.as_posix()}"

    try:
        command.upgrade(config, "head")
        assert database_path.exists()
        assert Base.metadata.tables == {}
    finally:
        if database_path.exists():
            database_path.unlink()
