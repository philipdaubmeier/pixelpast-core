"""Tests for Google Maps Timeline discovery, load, and connector boundaries."""

from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest

from pixelpast.ingestion.google_maps_timeline import (
    GoogleMapsTimelineConnector,
    GoogleMapsTimelineDocumentDescriptor,
    GoogleMapsTimelineDocumentDiscoverer,
    GoogleMapsTimelineDocumentFetcher,
    GoogleMapsTimelineDocumentLoadProgress,
    LoadedGoogleMapsTimelineExportDocument,
    resolve_google_maps_timeline_ingestion_root,
)
from pixelpast.shared.settings import Settings


def test_google_maps_timeline_root_resolution_requires_configured_root() -> None:
    settings = Settings(
        _env_file=None,
        google_maps_timeline_root=None,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Google Maps Timeline ingestion requires "
            "PIXELPAST_GOOGLE_MAPS_TIMELINE_ROOT to be configured."
        ),
    ):
        resolve_google_maps_timeline_ingestion_root(settings=settings)


def test_google_maps_timeline_discovery_accepts_exactly_one_json_file(
) -> None:
    workspace_root = _build_test_workspace("google-maps-discovery-file")

    try:
        export_path = workspace_root / "timeline-export.json"
        export_path.write_text('{"semanticSegments": []}', encoding="utf-8")

        discovered_labels: list[str] = []
        discovered = GoogleMapsTimelineDocumentDiscoverer().discover_documents(
            export_path,
            on_document_discovered=lambda descriptor, count: discovered_labels.append(
                f"{count}:{descriptor.origin_label}"
            ),
        )

        assert discovered == (
            GoogleMapsTimelineDocumentDescriptor(path=export_path.resolve()),
        )
        assert discovered_labels == [f"1:{export_path.resolve().as_posix()}"]
    finally:
        rmtree(workspace_root, ignore_errors=True)


def test_google_maps_timeline_discovery_rejects_missing_directory_and_non_json_roots(
) -> None:
    workspace_root = _build_test_workspace("google-maps-discovery-invalid")

    try:
        discoverer = GoogleMapsTimelineDocumentDiscoverer()
        missing_root = workspace_root / "missing.json"
        directory_root = workspace_root / "exports"
        unsupported_root = workspace_root / "timeline.txt"
        directory_root.mkdir()
        unsupported_root.write_text("{}", encoding="utf-8")

        with pytest.raises(ValueError, match="does not exist"):
            discoverer.discover_documents(missing_root)

        with pytest.raises(
            ValueError,
            match="must be a file, not a directory",
        ):
            discoverer.discover_documents(directory_root)

        with pytest.raises(ValueError, match=r"must be a \.json file"):
            discoverer.discover_documents(unsupported_root)
    finally:
        rmtree(workspace_root, ignore_errors=True)


def test_google_maps_timeline_fetcher_reads_utf8_text_and_preserves_descriptor_context(
) -> None:
    workspace_root = _build_test_workspace("google-maps-fetch")

    try:
        export_path = workspace_root / "timeline-export.json"
        export_text = '{"semanticSegments": [], "label": "Straße"}'
        export_path.write_text(export_text, encoding="utf-8")
        document = GoogleMapsTimelineDocumentDescriptor(path=export_path.resolve())

        progress_events: list[GoogleMapsTimelineDocumentLoadProgress] = []
        loaded_documents = GoogleMapsTimelineDocumentFetcher().fetch_documents(
            documents=(document,),
            on_document_progress=progress_events.append,
        )

        assert loaded_documents == (
            LoadedGoogleMapsTimelineExportDocument(
                descriptor=document,
                text=export_text,
            ),
        )
        assert (
            loaded_documents[0].descriptor.origin_label
            == export_path.resolve().as_posix()
        )
        assert progress_events == [
            GoogleMapsTimelineDocumentLoadProgress(
                event="submitted",
                document=document,
                document_index=1,
                document_total=1,
            ),
            GoogleMapsTimelineDocumentLoadProgress(
                event="completed",
                document=document,
                document_index=1,
                document_total=1,
            ),
        ]
    finally:
        rmtree(workspace_root, ignore_errors=True)


def test_google_maps_timeline_connector_delegates_discovery_and_raw_load(
) -> None:
    workspace_root = _build_test_workspace("google-maps-connector")

    try:
        export_path = workspace_root / "timeline-export.json"
        export_text = '{"semanticSegments": [], "rawSignals": []}'
        export_path.write_text(export_text, encoding="utf-8")

        connector = GoogleMapsTimelineConnector()
        discovered = connector.discover_documents(export_path)
        loaded = connector.fetch_documents(documents=discovered)

        assert discovered == (
            GoogleMapsTimelineDocumentDescriptor(path=export_path.resolve()),
        )
        assert loaded == (
            LoadedGoogleMapsTimelineExportDocument(
                descriptor=discovered[0],
                text=export_text,
            ),
        )
    finally:
        rmtree(workspace_root, ignore_errors=True)


def _build_test_workspace(prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
