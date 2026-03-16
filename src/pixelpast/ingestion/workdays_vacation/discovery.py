"""Filesystem discovery for workdays-vacation workbook ingestion."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from pixelpast.ingestion.workdays_vacation.contracts import (
    WorkdaysVacationWorkbookDescriptor,
)

_SUPPORTED_FILE_EXTENSIONS = frozenset({".xlsx"})


class WorkdaysVacationWorkbookDiscoverer:
    """Discover supported workbook files from one root path."""

    def discover_workbooks(
        self,
        root: Path,
        *,
        on_workbook_discovered: (
            Callable[[WorkdaysVacationWorkbookDescriptor, int], None] | None
        ) = None,
    ) -> list[WorkdaysVacationWorkbookDescriptor]:
        """Return supported workbook files beneath one validated root."""

        resolved_root = root.expanduser().resolve()
        if not resolved_root.exists():
            raise ValueError(
                f"Workdays vacation root does not exist: {resolved_root}"
            )

        discovered_workbooks = list(self._discover_from_root(root=resolved_root))
        if on_workbook_discovered is not None:
            for index, workbook in enumerate(discovered_workbooks, start=1):
                on_workbook_discovered(workbook, index)
        return discovered_workbooks

    def _discover_from_root(
        self,
        *,
        root: Path,
    ) -> Iterable[WorkdaysVacationWorkbookDescriptor]:
        if root.is_file():
            if root.suffix.lower() not in _SUPPORTED_FILE_EXTENSIONS:
                raise ValueError(f"Workdays vacation root is not supported: {root}")
            return self._discover_from_file(path=root)
        if root.is_dir():
            return self._discover_from_directory(root=root)
        raise ValueError(
            f"Workdays vacation root is neither file nor directory: {root}"
        )

    def _discover_from_directory(
        self,
        *,
        root: Path,
    ) -> Iterable[WorkdaysVacationWorkbookDescriptor]:
        for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix()):
            if path.is_file() and path.suffix.lower() in _SUPPORTED_FILE_EXTENSIONS:
                yield from self._discover_from_file(path=path)

    def _discover_from_file(
        self,
        *,
        path: Path,
    ) -> Iterable[WorkdaysVacationWorkbookDescriptor]:
        if path.suffix.lower() != ".xlsx":
            raise ValueError(f"Workdays vacation workbook is not supported: {path}")
        yield WorkdaysVacationWorkbookDescriptor(path=path)


__all__ = ["WorkdaysVacationWorkbookDiscoverer"]
