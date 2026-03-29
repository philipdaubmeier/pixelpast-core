"""Shared session-bound base for staged ingestion persistence scopes."""

from __future__ import annotations

from sqlalchemy.orm import Session

from pixelpast.shared.runtime import RuntimeContext


class SessionBoundPersistenceScopeBase:
    """Own the repeated session lifecycle shell for staged persistence scopes."""

    def __init__(self, *, runtime: RuntimeContext) -> None:
        self._session: Session = runtime.session_factory()

    def commit(self) -> None:
        """Commit the open transaction."""

        self._session.commit()

    def rollback(self) -> None:
        """Rollback the open transaction."""

        self._session.rollback()

    def close(self) -> None:
        """Close the open session."""

        self._session.close()


__all__ = ["SessionBoundPersistenceScopeBase"]
