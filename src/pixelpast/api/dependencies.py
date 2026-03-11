"""FastAPI dependency providers."""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session, sessionmaker


def create_db_session_dependency(
    session_factory: sessionmaker[Session],
) -> Generator[Session, None, None]:
    """Yield request-scoped database sessions from a session factory."""

    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_db_session(request: Request) -> Generator[Session, None, None]:
    """Yield a request-scoped session from the application state."""

    session_factory: sessionmaker[Session] = request.app.state.session_factory
    yield from create_db_session_dependency(session_factory)
