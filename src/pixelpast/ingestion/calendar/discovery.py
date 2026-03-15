"""Filesystem and archive discovery for calendar ingestion."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from pixelpast.ingestion.calendar.contracts import CalendarDocumentDescriptor

_SUPPORTED_FILE_EXTENSIONS = frozenset({".ics", ".zip"})


class CalendarDocumentDiscoverer:
    """Discover filesystem and zip-backed calendar documents from one root."""

    def discover_documents(
        self,
        root: Path,
        *,
        on_document_discovered: Callable[[CalendarDocumentDescriptor, int], None]
        | None = None,
    ) -> list[CalendarDocumentDescriptor]:
        """Return supported calendar documents beneath one validated root."""

        resolved_root = root.expanduser().resolve()
        if not resolved_root.exists():
            raise ValueError(f"Calendar root does not exist: {resolved_root}")

        discovered_documents = list(self._discover_from_root(root=resolved_root))
        if on_document_discovered is not None:
            for index, document in enumerate(discovered_documents, start=1):
                on_document_discovered(document, index)
        return discovered_documents

    def _discover_from_root(
        self,
        *,
        root: Path,
    ) -> Iterable[CalendarDocumentDescriptor]:
        if root.is_file():
            if root.suffix.lower() not in _SUPPORTED_FILE_EXTENSIONS:
                raise ValueError(f"Calendar root is not supported: {root}")
            return self._discover_from_file(path=root)
        if root.is_dir():
            return self._discover_from_directory(root=root)
        raise ValueError(f"Calendar root is neither file nor directory: {root}")

    def _discover_from_directory(
        self,
        *,
        root: Path,
    ) -> Iterable[CalendarDocumentDescriptor]:
        for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix()):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix not in _SUPPORTED_FILE_EXTENSIONS:
                continue
            yield from self._discover_from_file(path=path)

    def _discover_from_file(
        self,
        *,
        path: Path,
    ) -> Iterable[CalendarDocumentDescriptor]:
        suffix = path.suffix.lower()
        if suffix == ".ics":
            yield CalendarDocumentDescriptor(path=path)
            return
        if suffix == ".zip":
            yield from self._discover_from_zip(path=path)
            return
        raise ValueError(f"Calendar file is not supported: {path}")

    def _discover_from_zip(self, *, path: Path) -> Iterable[CalendarDocumentDescriptor]:
        try:
            with ZipFile(path) as archive:
                member_names = sorted(
                    (
                        member.filename.replace("\\", "/")
                        for member in archive.infolist()
                        if not member.is_dir()
                        and member.filename.lower().endswith(".ics")
                    ),
                )
        except BadZipFile as error:
            raise ValueError(f"Calendar zip file is invalid: {path}") from error

        for member_name in member_names:
            yield CalendarDocumentDescriptor(
                path=path,
                archive_member_path=member_name,
            )


__all__ = ["CalendarDocumentDiscoverer"]
