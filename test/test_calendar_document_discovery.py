"""Tests for calendar filesystem discovery and raw document loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from pixelpast.ingestion.calendar import (
    CalendarDocumentDescriptor,
    CalendarDocumentDiscoverer,
    CalendarDocumentFetcher,
    CalendarDocumentLoadProgress,
)


@dataclass(frozen=True)
class _FakeZipMember:
    filename: str
    directory: bool = False

    def is_dir(self) -> bool:
        return self.directory


class _FakeZipArchive:
    def __init__(
        self,
        path: Path,
        *,
        members: list[_FakeZipMember] | None = None,
        payloads: dict[str, bytes] | None = None,
    ) -> None:
        del path
        self._members = members or []
        self._payloads = payloads or {}

    def __enter__(self) -> _FakeZipArchive:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb

    def infolist(self) -> list[_FakeZipMember]:
        return list(self._members)

    def read(self, member_name: str) -> bytes:
        return self._payloads[member_name]


def test_calendar_discovery_accepts_single_ics_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calendar_path = Path("virtual/single.ics")
    resolved_calendar_path = calendar_path.resolve()

    monkeypatch.setattr(
        Path,
        "exists",
        lambda self: self == resolved_calendar_path,
    )
    monkeypatch.setattr(
        Path,
        "is_file",
        lambda self: self == resolved_calendar_path,
    )
    monkeypatch.setattr(Path, "is_dir", lambda self: False)

    discovered = CalendarDocumentDiscoverer().discover_documents(calendar_path)

    assert discovered == [CalendarDocumentDescriptor(path=resolved_calendar_path)]


def test_calendar_discovery_recursively_discovers_ics_and_zip_members_in_stable_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path("virtual/root")
    first_ics = root / "a-sub" / "one.ics"
    second_ics = root / "b-sub" / "two.ics"
    archive_path = root / "calendar-bundle.zip"
    resolved_root = root.resolve()
    resolved_first_ics = first_ics.resolve()
    resolved_second_ics = second_ics.resolve()
    resolved_archive_path = archive_path.resolve()
    resolved_a_sub = (root / "a-sub").resolve()
    resolved_b_sub = (root / "b-sub").resolve()
    resolved_ignored = (root / "ignored.txt").resolve()
    directory_entries = [
        resolved_b_sub,
        resolved_a_sub,
        resolved_first_ics,
        resolved_second_ics,
        resolved_archive_path,
        resolved_ignored,
    ]

    monkeypatch.setattr(Path, "exists", lambda self: self == resolved_root)
    monkeypatch.setattr(
        Path,
        "is_dir",
        lambda self: self == resolved_root or self in {resolved_a_sub, resolved_b_sub},
    )
    monkeypatch.setattr(
        Path,
        "is_file",
        lambda self: self
        in {
            resolved_first_ics,
            resolved_second_ics,
            resolved_archive_path,
            resolved_ignored,
        },
    )
    monkeypatch.setattr(
        Path,
        "rglob",
        lambda self, pattern: (
            directory_entries if self == resolved_root and pattern == "*" else []
        ),
    )
    monkeypatch.setattr(
        "pixelpast.ingestion.calendar.discovery.ZipFile",
        lambda path: _FakeZipArchive(
            path,
            members=[
                _FakeZipMember("z-last.ics"),
                _FakeZipMember("nested/a-first.ics"),
                _FakeZipMember("ignored.txt"),
            ],
        ),
    )

    callback_labels: list[str] = []
    discovered = CalendarDocumentDiscoverer().discover_documents(
        root,
        on_document_discovered=lambda document, count: callback_labels.append(
            f"{count}:{document.origin_label}"
        ),
    )

    assert [
        (document.path.name, document.archive_member_path) for document in discovered
    ] == [
        ("one.ics", None),
        ("two.ics", None),
        ("calendar-bundle.zip", "nested/a-first.ics"),
        ("calendar-bundle.zip", "z-last.ics"),
    ]
    assert callback_labels == [
        f"1:{resolved_first_ics.as_posix()}",
        f"2:{resolved_second_ics.as_posix()}",
        f"3:{resolved_archive_path.as_posix()}::nested/a-first.ics",
        f"4:{resolved_archive_path.as_posix()}::z-last.ics",
    ]


def test_calendar_discovery_accepts_single_zip_root_and_emits_archive_members(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_path = Path("virtual/calendar-bundle.zip")
    resolved_archive_path = archive_path.resolve()

    monkeypatch.setattr(Path, "exists", lambda self: self == resolved_archive_path)
    monkeypatch.setattr(Path, "is_file", lambda self: self == resolved_archive_path)
    monkeypatch.setattr(Path, "is_dir", lambda self: False)
    monkeypatch.setattr(
        "pixelpast.ingestion.calendar.discovery.ZipFile",
        lambda path: _FakeZipArchive(
            path,
            members=[
                _FakeZipMember("nested/work.ics"),
                _FakeZipMember("home.ics"),
            ],
        ),
    )

    discovered = CalendarDocumentDiscoverer().discover_documents(archive_path)

    assert discovered == [
        CalendarDocumentDescriptor(
            path=resolved_archive_path,
            archive_member_path="home.ics",
        ),
        CalendarDocumentDescriptor(
            path=resolved_archive_path,
            archive_member_path="nested/work.ics",
        ),
    ]


def test_calendar_discovery_rejects_missing_and_unsupported_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_root = Path("virtual/missing")
    unsupported_path = Path("virtual/notes.txt")
    resolved_unsupported_path = unsupported_path.resolve()

    monkeypatch.setattr(Path, "exists", lambda self: self == resolved_unsupported_path)
    monkeypatch.setattr(Path, "is_file", lambda self: self == resolved_unsupported_path)
    monkeypatch.setattr(Path, "is_dir", lambda self: False)

    discoverer = CalendarDocumentDiscoverer()

    with pytest.raises(ValueError, match="does not exist"):
        discoverer.discover_documents(missing_root)

    with pytest.raises(ValueError, match="not supported"):
        discoverer.discover_documents(unsupported_path)


def test_calendar_fetcher_reads_plain_and_zip_backed_documents_without_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plain_path = Path("virtual/plain.ics")
    archive_path = Path("virtual/calendar-bundle.zip")
    documents = [
        CalendarDocumentDescriptor(path=plain_path.resolve()),
        CalendarDocumentDescriptor(
            path=archive_path.resolve(),
            archive_member_path="nested/work.ics",
        ),
    ]

    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda self: (
            b"BEGIN:VCALENDAR\nX-WR-CALNAME:Plain\nEND:VCALENDAR\n"
            if self == plain_path.resolve()
            else b""
        ),
    )
    monkeypatch.setattr(
        "pixelpast.ingestion.calendar.fetch.ZipFile",
        lambda path: _FakeZipArchive(
            path,
            payloads={
                "nested/work.ics": (
                    b"BEGIN:VCALENDAR\nX-WR-CALNAME:Work\nEND:VCALENDAR\n"
                ),
            },
        ),
    )

    progress_events: list[CalendarDocumentLoadProgress] = []
    fetched = CalendarDocumentFetcher().fetch_text_by_descriptor(
        documents=documents,
        on_document_progress=progress_events.append,
    )

    assert fetched[documents[0]] == (
        "BEGIN:VCALENDAR\nX-WR-CALNAME:Plain\nEND:VCALENDAR\n"
    )
    assert fetched[documents[1]] == (
        "BEGIN:VCALENDAR\nX-WR-CALNAME:Work\nEND:VCALENDAR\n"
    )
    assert progress_events == [
        CalendarDocumentLoadProgress(
            event="submitted",
            document=documents[0],
            document_index=1,
            document_total=2,
        ),
        CalendarDocumentLoadProgress(
            event="completed",
            document=documents[0],
            document_index=1,
            document_total=2,
        ),
        CalendarDocumentLoadProgress(
            event="submitted",
            document=documents[1],
            document_index=2,
            document_total=2,
        ),
        CalendarDocumentLoadProgress(
            event="completed",
            document=documents[1],
            document_index=2,
            document_total=2,
        ),
    ]


def test_calendar_descriptor_origin_label_includes_archive_context() -> None:
    archive_path = Path("virtual/calendar-bundle.zip")
    descriptor = CalendarDocumentDescriptor(
        path=archive_path,
        archive_member_path="nested/work.ics",
    )

    assert descriptor.is_archive_member is True
    assert descriptor.origin_path == archive_path.resolve()
    assert (
        descriptor.origin_label
        == f"{archive_path.resolve().as_posix()}::nested/work.ics"
    )
