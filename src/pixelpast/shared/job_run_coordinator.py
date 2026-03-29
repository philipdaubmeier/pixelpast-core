"""Shared job-run bootstrap base for ingest and derive coordinators."""

from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from pixelpast.persistence.repositories import JobRunRepository
from pixelpast.shared.progress import build_initial_job_progress_payload
from pixelpast.shared.runtime import RuntimeContext


class JobRunCoordinatorBase(ABC):
    """Centralize the common persisted job-run bootstrap shell."""

    job_type: str
    job_name: str
    mode: str
    initial_phase: str

    def _create_run(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path | None = None,
        job_name: str | None = None,
        mode: str | None = None,
        **kwargs: Any,
    ) -> int:
        """Persist one initialized job run after optional source bootstrap."""

        session = runtime.session_factory()
        try:
            self._bootstrap_source_state(
                session=session,
                runtime=runtime,
                resolved_root=resolved_root,
                **kwargs,
            )
            job_run = JobRunRepository(session).create(
                job_type=self.job_type,
                job=job_name or self.job_name,
                mode=mode or self.mode,
                phase=self.initial_phase,
                progress_json=self._build_progress_payload(
                    runtime=runtime,
                    resolved_root=resolved_root,
                    **kwargs,
                ),
            )
            session.commit()
            return job_run.id
        finally:
            session.close()

    def _bootstrap_source_state(
        self,
        *,
        session: Session,
        runtime: RuntimeContext,
        resolved_root: Path | None = None,
        **kwargs: Any,
    ) -> None:
        """Allow coordinators to prepare source state before run creation."""

        del session, runtime, resolved_root, kwargs

    def _build_progress_payload(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path | None = None,
        **kwargs: Any,
    ) -> dict[str, int | str | None]:
        """Return the initial persisted progress payload for a new run."""

        del runtime, kwargs
        payload: dict[str, int | str | None] = build_initial_job_progress_payload()
        if resolved_root is not None and self._include_root_path_in_payload():
            payload["root_path"] = resolved_root.as_posix()
        return payload

    def _include_root_path_in_payload(self) -> bool:
        """Return whether the coordinator persists the root path on init."""

        return False


__all__ = ["JobRunCoordinatorBase"]
