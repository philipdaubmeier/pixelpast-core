"""Tests for Spotify JSON discovery and account grouping boundaries."""

from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from uuid import uuid4
from zipfile import ZipFile

from pixelpast.ingestion.spotify import (
    SpotifyAccountDocumentGroup,
    SpotifyStreamingHistoryDiscoveryResult,
    SpotifyStreamingHistoryDocumentDescriptor,
    SpotifyStreamingHistoryDocumentDiscoverer,
    group_spotify_documents_by_account,
    parse_spotify_streaming_history_document,
    resolve_spotify_ingestion_root,
)
from pixelpast.shared.settings import Settings


def test_spotify_discovery_accepts_supported_direct_json_file() -> None:
    workspace_root = _build_test_workspace("spotify-discovery-file")

    try:
        document_path = workspace_root / "Streaming_History_Audio_2024.json"
        document_path.write_text("[]", encoding="utf-8")

        result = SpotifyStreamingHistoryDocumentDiscoverer().discover_documents(
            document_path
        )

        assert result == SpotifyStreamingHistoryDiscoveryResult(
            documents=(
                SpotifyStreamingHistoryDocumentDescriptor(path=document_path.resolve()),
            ),
            skipped_json_file_count=0,
        )
    finally:
        rmtree(workspace_root, ignore_errors=True)


def test_spotify_discovery_walks_directories_recursively_in_deterministic_order() -> (
    None
):
    workspace_root = _build_test_workspace("spotify-discovery-dir")

    try:
        supported_root = workspace_root / "takeout"
        supported_root.mkdir()
        second_document = (
            supported_root / "z-last" / "Streaming_History_Audio_2025.json"
        )
        first_document = (
            supported_root / "a-first" / "Streaming_History_Audio_2024.json"
        )
        skipped_document = supported_root / "nested" / "PlaylistMetadata.json"
        first_document.parent.mkdir(parents=True)
        second_document.parent.mkdir(parents=True)
        skipped_document.parent.mkdir(parents=True)
        first_document.write_text("[]", encoding="utf-8")
        second_document.write_text("[]", encoding="utf-8")
        skipped_document.write_text("{}", encoding="utf-8")

        discovered_paths: list[str] = []
        result = SpotifyStreamingHistoryDocumentDiscoverer().discover_documents(
            supported_root,
            on_document_discovered=lambda descriptor, _count: discovered_paths.append(
                descriptor.origin_label
            ),
        )

        assert result == SpotifyStreamingHistoryDiscoveryResult(
            documents=(
                SpotifyStreamingHistoryDocumentDescriptor(
                    path=first_document.resolve()
                ),
                SpotifyStreamingHistoryDocumentDescriptor(
                    path=second_document.resolve()
                ),
            ),
            skipped_json_file_count=1,
        )
        assert discovered_paths == [
            first_document.resolve().as_posix(),
            second_document.resolve().as_posix(),
        ]
    finally:
        rmtree(workspace_root, ignore_errors=True)


def test_spotify_discovery_accepts_single_zip_root_and_emits_archive_members() -> None:
    workspace_root = _build_test_workspace("spotify-discovery-zip")

    try:
        archive_path = workspace_root / "spotify-export.zip"
        with ZipFile(archive_path, mode="w") as archive:
            archive.writestr("nested/Streaming_History_Audio_2024.json", "[]")
            archive.writestr("Streaming_History_Video_2024.json", "[]")
            archive.writestr("nested/PlaylistMetadata.json", "{}")

        result = SpotifyStreamingHistoryDocumentDiscoverer().discover_documents(
            archive_path
        )

        assert result == SpotifyStreamingHistoryDiscoveryResult(
            documents=(
                SpotifyStreamingHistoryDocumentDescriptor(
                    path=archive_path.resolve(),
                    archive_member_path="Streaming_History_Video_2024.json",
                ),
                SpotifyStreamingHistoryDocumentDescriptor(
                    path=archive_path.resolve(),
                    archive_member_path="nested/Streaming_History_Audio_2024.json",
                ),
            ),
            skipped_json_file_count=1,
        )
    finally:
        rmtree(workspace_root, ignore_errors=True)


def test_spotify_discovery_recurses_directories_and_zip_members() -> None:
    workspace_root = _build_test_workspace("spotify-discovery-dir-zip")

    try:
        root = workspace_root / "takeout"
        root.mkdir()
        direct_document = root / "Streaming_History_Audio_2024.json"
        archive_path = root / "bundle.zip"
        direct_document.write_text("[]", encoding="utf-8")
        with ZipFile(archive_path, mode="w") as archive:
            archive.writestr("nested/Streaming_History_Video_2025.json", "[]")
            archive.writestr("nested/Profile.json", "{}")

        result = SpotifyStreamingHistoryDocumentDiscoverer().discover_documents(root)

        assert result == SpotifyStreamingHistoryDiscoveryResult(
            documents=(
                SpotifyStreamingHistoryDocumentDescriptor(
                    path=direct_document.resolve()
                ),
                SpotifyStreamingHistoryDocumentDescriptor(
                    path=archive_path.resolve(),
                    archive_member_path="nested/Streaming_History_Video_2025.json",
                ),
            ),
            skipped_json_file_count=1,
        )
    finally:
        rmtree(workspace_root, ignore_errors=True)


def test_spotify_root_resolution_requires_configured_root() -> None:
    settings = Settings(
        _env_file=None,
        spotify_root=None,
    )

    try:
        resolve_spotify_ingestion_root(settings=settings)
    except ValueError as error:
        assert str(error) == (
            "Spotify ingestion requires PIXELPAST_SPOTIFY_ROOT to be configured."
        )
    else:
        raise AssertionError("Expected Spotify root resolution to fail.")


def test_spotify_account_grouping_keeps_document_boundary_and_merges_by_username() -> (
    None
):
    workspace_root = _build_test_workspace("spotify-grouping")

    try:
        first_document_path = workspace_root / "Streaming_History_Audio_2024.json"
        second_document_path = (
            workspace_root / "nested" / "Streaming_History_Audio_2025.json"
        )
        second_document_path.parent.mkdir(parents=True)
        first_document_path.write_text("[]", encoding="utf-8")
        second_document_path.write_text("[]", encoding="utf-8")

        first_document = parse_spotify_streaming_history_document(
            descriptor=SpotifyStreamingHistoryDocumentDescriptor(
                path=first_document_path
            ),
            text=(
                "["
                '{"ts":"2024-02-01T07:15:10Z","username":"PixelUser",'
                '"platform":"android","ms_played":1000,"conn_country":"DE",'
                '"master_metadata_track_name":"One",'
                '"master_metadata_album_artist_name":"Artist",'
                '"spotify_track_uri":"spotify:track:1",'
                '"episode_name":null,"episode_show_name":null,'
                '"spotify_episode_uri":null,"shuffle":false,"skipped":false},'
                '{"ts":"2024-02-01T08:15:10Z","username":"SecondUser",'
                '"platform":"web","ms_played":2000,"conn_country":"DE",'
                '"master_metadata_track_name":"Two",'
                '"master_metadata_album_artist_name":"Artist",'
                '"spotify_track_uri":"spotify:track:2",'
                '"episode_name":null,"episode_show_name":null,'
                '"spotify_episode_uri":null,"shuffle":false,"skipped":false}'
                "]"
            ),
        )
        second_document = parse_spotify_streaming_history_document(
            descriptor=SpotifyStreamingHistoryDocumentDescriptor(
                path=second_document_path
            ),
            text=(
                "["
                '{"ts":"2024-02-02T07:15:10Z","username":" pixeluser ",'
                '"platform":"android","ms_played":3000,"conn_country":"DE",'
                '"master_metadata_track_name":"Three",'
                '"master_metadata_album_artist_name":"Artist",'
                '"spotify_track_uri":"spotify:track:3",'
                '"episode_name":null,"episode_show_name":null,'
                '"spotify_episode_uri":null,"shuffle":true,"skipped":false}'
                "]"
            ),
        )

        groups = group_spotify_documents_by_account([second_document, first_document])

        assert groups == (
            SpotifyAccountDocumentGroup(
                normalized_username="pixeluser",
                source_external_id="spotify:pixeluser",
                documents=(first_document, second_document),
                rows=(
                    first_document.rows[0],
                    second_document.rows[0],
                ),
            ),
            SpotifyAccountDocumentGroup(
                normalized_username="seconduser",
                source_external_id="spotify:seconduser",
                documents=(first_document,),
                rows=(first_document.rows[1],),
            ),
        )
    finally:
        rmtree(workspace_root, ignore_errors=True)


def _build_test_workspace(prefix: str) -> Path:
    workspace_root = Path("var") / f"{prefix}-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root
