"""Tests for the shared session-bound persistence scope base."""

from __future__ import annotations

from dataclasses import dataclass

from pixelpast.ingestion.persistence_base import SessionBoundPersistenceScopeBase


def test_session_bound_persistence_scope_base_delegates_session_lifecycle() -> None:
    session = _FakeSession()
    runtime = _FakeRuntime(session=session)

    scope = SessionBoundPersistenceScopeBase(runtime=runtime)

    scope.commit()
    scope.rollback()
    scope.close()

    assert runtime.session_factory_calls == 1
    assert session.commit_calls == 1
    assert session.rollback_calls == 1
    assert session.close_calls == 1


@dataclass
class _FakeRuntime:
    session: _FakeSession
    session_factory_calls: int = 0

    def session_factory(self) -> _FakeSession:
        self.session_factory_calls += 1
        return self.session


@dataclass
class _FakeSession:
    commit_calls: int = 0
    rollback_calls: int = 0
    close_calls: int = 0

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.close_calls += 1
