"""Raw content loading for discovered calendar documents."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from zipfile import BadZipFile, ZipFile

from pixelpast.ingestion.calendar.contracts import CalendarDocumentDescriptor

_TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252")


@dataclass(slots=True, frozen=True)
class CalendarDocumentLoadProgress:
    """Represents one raw calendar document load transition."""

    event: str
    document: CalendarDocumentDescriptor
    document_index: int
    document_total: int


class CalendarDocumentFetcher:
    """Load raw ICS text for discovered plain files and zip members."""

    def fetch_text_by_descriptor(
        self,
        *,
        documents: Sequence[CalendarDocumentDescriptor],
        on_document_progress: (
            Callable[[CalendarDocumentLoadProgress], None] | None
        ) = None,
    ) -> dict[CalendarDocumentDescriptor, str]:
        """Return raw calendar text indexed by document descriptor."""

        fetched_documents: dict[CalendarDocumentDescriptor, str] = {}
        document_total = len(documents)
        for index, document in enumerate(documents, start=1):
            if on_document_progress is not None:
                on_document_progress(
                    CalendarDocumentLoadProgress(
                        event="submitted",
                        document=document,
                        document_index=index,
                        document_total=document_total,
                    )
                )
            fetched_documents[document] = self._fetch_document_text(document=document)
            if on_document_progress is not None:
                on_document_progress(
                    CalendarDocumentLoadProgress(
                        event="completed",
                        document=document,
                        document_index=index,
                        document_total=document_total,
                    )
                )
        return fetched_documents

    def _fetch_document_text(self, *, document: CalendarDocumentDescriptor) -> str:
        if document.archive_member_path is None:
            return _decode_calendar_bytes(document.path.read_bytes())
        return self._read_archive_member(document=document)

    def _read_archive_member(self, *, document: CalendarDocumentDescriptor) -> str:
        try:
            with ZipFile(document.path) as archive:
                try:
                    member_bytes = archive.read(document.archive_member_path)
                except KeyError as error:
                    raise ValueError(
                        "Calendar archive member does not exist: "
                        f"{document.origin_label}"
                    ) from error
        except BadZipFile as error:
            raise ValueError(
                f"Calendar zip file is invalid: {document.path}"
            ) from error

        return _decode_calendar_bytes(member_bytes)


def _decode_calendar_bytes(payload: bytes) -> str:
    for encoding in _TEXT_ENCODINGS:
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


__all__ = ["CalendarDocumentFetcher", "CalendarDocumentLoadProgress"]
