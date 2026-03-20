"""Integration tests for Spotify staged ingestion persistence and lifecycle."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from pixelpast.ingestion.spotify import SpotifyIngestionService
from pixelpast.persistence.models import Asset, Event, JobRun, Source
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings


def test_spotify_ingestion_merges_multiple_documents_per_account_into_one_source(
) -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        first_document = workspace_root / "Streaming_History_Audio_2024.json"
        second_document = workspace_root / "nested" / "Streaming_History_Audio_2025.json"
        skipped_document = workspace_root / "nested" / "PlaylistMetadata.json"
        second_document.parent.mkdir(parents=True)
        first_document.write_text(
            _build_spotify_document(
                [
                    _spotify_row(
                        ts="2024-02-01T07:15:10Z",
                        username="PixelUser",
                        ms_played=1000,
                        track="One",
                    ),
                    _spotify_row(
                        ts="2024-02-01T08:15:10Z",
                        username="PixelUser",
                        ms_played=2000,
                        track="Two",
                    ),
                ]
            ),
            encoding="utf-8",
        )
        second_document.write_text(
            _build_spotify_document(
                [
                    _spotify_row(
                        ts="2024-02-02T07:15:10Z",
                        username=" pixeluser ",
                        ms_played=3000,
                        track="Three",
                        shuffle=True,
                    )
                ]
            ),
            encoding="utf-8",
        )
        skipped_document.write_text("{}", encoding="utf-8")

        result = SpotifyIngestionService().ingest(runtime=runtime, root=workspace_root)

        with runtime.session_factory() as session:
            source = session.execute(select(Source)).scalar_one()
            events = list(
                session.execute(select(Event).order_by(Event.timestamp_end, Event.id)).scalars()
            )
            job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalar_one()

        assert result.status == "completed"
        assert result.processed_document_count == 2
        assert result.persisted_source_count == 1
        assert result.persisted_event_count == 3
        assert result.error_count == 0
        assert result.skipped_json_file_count == 1
        assert source.type == "spotify"
        assert source.external_id == "spotify:pixeluser"
        assert source.config == {
            "username": "pixeluser",
            "origin_labels": sorted(
                [
                    first_document.resolve().as_posix(),
                    second_document.resolve().as_posix(),
                ]
            ),
        }
        assert [event.title for event in events] == [
            "Artist - One",
            "Artist - Two",
            "Artist - Three",
        ]
        assert job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 3,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
            "persisted_event_count": 3,
        }
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_spotify_ingestion_is_idempotent_for_same_account_file_set() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        document = workspace_root / "Streaming_History_Audio_2024.json"
        document.write_text(
            _build_spotify_document(
                [
                    _spotify_row(
                        ts="2024-02-01T07:15:10Z",
                        username="PixelUser",
                        ms_played=1000,
                        track="One",
                    ),
                    _spotify_row(
                        ts="2024-02-01T08:15:10Z",
                        username="PixelUser",
                        ms_played=2000,
                        track="Two",
                    ),
                ]
            ),
            encoding="utf-8",
        )

        first_result = SpotifyIngestionService().ingest(runtime=runtime, root=document)
        with runtime.session_factory() as session:
            first_source = session.execute(select(Source)).scalar_one()
            first_events = list(
                session.execute(select(Event).order_by(Event.timestamp_end, Event.id)).scalars()
            )

        second_result = SpotifyIngestionService().ingest(runtime=runtime, root=document)
        with runtime.session_factory() as session:
            second_source = session.execute(select(Source)).scalar_one()
            second_events = list(
                session.execute(select(Event).order_by(Event.timestamp_end, Event.id)).scalars()
            )
            latest_job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalars().first()

        assert first_result.status == "completed"
        assert second_result.status == "completed"
        assert first_source.id == second_source.id
        assert [event.id for event in first_events] == [event.id for event in second_events]
        assert [event.created_at for event in first_events] == [
            event.created_at for event in second_events
        ]
        assert latest_job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 0,
            "updated": 0,
            "unchanged": 2,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
            "persisted_event_count": 2,
        }
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_spotify_ingestion_replaces_full_account_event_set_when_documents_change(
) -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        first_document = workspace_root / "Streaming_History_Audio_2024.json"
        second_document = workspace_root / "Streaming_History_Audio_2025.json"
        first_document.write_text(
            _build_spotify_document(
                [
                    _spotify_row(
                        ts="2024-02-01T07:15:10Z",
                        username="PixelUser",
                        ms_played=1000,
                        track="One",
                    )
                ]
            ),
            encoding="utf-8",
        )
        second_document.write_text(
            _build_spotify_document(
                [
                    _spotify_row(
                        ts="2024-02-01T08:15:10Z",
                        username="PixelUser",
                        ms_played=2000,
                        track="Two",
                    ),
                    _spotify_row(
                        ts="2024-02-01T09:15:10Z",
                        username="PixelUser",
                        ms_played=3000,
                        track="Three",
                    ),
                ]
            ),
            encoding="utf-8",
        )

        SpotifyIngestionService().ingest(runtime=runtime, root=workspace_root)
        with runtime.session_factory() as session:
            original_source = session.execute(select(Source)).scalar_one()
            original_events = list(
                session.execute(select(Event).order_by(Event.timestamp_end, Event.id)).scalars()
            )

        second_document.write_text(
            _build_spotify_document(
                [
                    _spotify_row(
                        ts="2024-02-02T08:15:10Z",
                        username="PixelUser",
                        ms_played=2000,
                        track="Replacement",
                    )
                ]
            ),
            encoding="utf-8",
        )

        result = SpotifyIngestionService().ingest(runtime=runtime, root=workspace_root)

        with runtime.session_factory() as session:
            source = session.execute(select(Source)).scalar_one()
            events = list(
                session.execute(select(Event).order_by(Event.timestamp_end, Event.id)).scalars()
            )
            latest_job_run = session.execute(
                select(JobRun).order_by(JobRun.id.desc())
            ).scalars().first()

        assert result.status == "completed"
        assert result.persisted_source_count == 1
        assert result.persisted_event_count == 2
        assert source.id == original_source.id
        assert [event.id for event in events] != [event.id for event in original_events]
        assert [event.title for event in events] == [
            "Artist - One",
            "Artist - Replacement",
        ]
        assert latest_job_run.progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 0,
            "updated": 2,
            "unchanged": 0,
            "skipped": 0,
            "failed": 0,
            "missing_from_source": 0,
            "persisted_event_count": 2,
        }
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_spotify_ingestion_preserves_exact_duplicate_rows_for_v1() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        document = workspace_root / "Streaming_History_Audio_2024.json"
        duplicate_row = _spotify_row(
            ts="2024-02-01T07:15:10Z",
            username="PixelUser",
            ms_played=1000,
            track="One",
        )
        document.write_text(
            _build_spotify_document([duplicate_row, duplicate_row]),
            encoding="utf-8",
        )

        result = SpotifyIngestionService().ingest(runtime=runtime, root=document)

        with runtime.session_factory() as session:
            events = list(
                session.execute(select(Event).order_by(Event.id)).scalars()
            )

        assert result.status == "completed"
        assert result.persisted_event_count == 2
        assert len(events) == 2
        assert [event.title for event in events] == ["Artist - One", "Artist - One"]
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_spotify_ingestion_creates_one_source_per_account_for_multi_account_input() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    try:
        first_document = workspace_root / "Streaming_History_Audio_2024.json"
        second_document = workspace_root / "nested" / "Streaming_History_Audio_2025.json"
        second_document.parent.mkdir(parents=True)
        first_document.write_text(
            _build_spotify_document(
                [
                    _spotify_row(
                        ts="2024-02-01T07:15:10Z",
                        username="PixelUser",
                        ms_played=1000,
                        track="One",
                    )
                ]
            ),
            encoding="utf-8",
        )
        second_document.write_text(
            _build_spotify_document(
                [
                    _spotify_row(
                        ts="2024-02-01T08:15:10Z",
                        username="SecondUser",
                        ms_played=2000,
                        track="Two",
                    ),
                ]
            ),
            encoding="utf-8",
        )

        result = SpotifyIngestionService().ingest(runtime=runtime, root=workspace_root)

        with runtime.session_factory() as session:
            sources = list(
                session.execute(select(Source).order_by(Source.external_id)).scalars()
            )
            events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_end, Event.id)
                ).scalars()
            )

        assert result.status == "completed"
        assert result.processed_document_count == 2
        assert result.persisted_source_count == 2
        assert result.persisted_event_count == 2
        assert [source.external_id for source in sources] == [
            "spotify:pixeluser",
            "spotify:seconduser",
        ]
        assert [event.title for event in events] == ["Artist - One", "Artist - Two"]
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_spotify_ingestion_persists_canonical_mapping_without_assets() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    fixture_path = Path("test/assets/spotify_streaming_history_audio_test_fixture.json")
    document = workspace_root / "Streaming_History_Audio_2024.json"
    document.write_text(fixture_path.read_text(encoding="utf-8"), encoding="utf-8")

    try:
        result = SpotifyIngestionService().ingest(runtime=runtime, root=document)

        with runtime.session_factory() as session:
            sources = list(session.execute(select(Source).order_by(Source.id)).scalars())
            events = list(
                session.execute(
                    select(Event).order_by(Event.timestamp_end, Event.id)
                ).scalars()
            )
            assets = list(session.execute(select(Asset).order_by(Asset.id)).scalars())

        assert result.status == "completed"
        assert result.processed_document_count == 1
        assert result.persisted_source_count == 1
        assert result.persisted_event_count == 2
        assert assets == []
        assert len(sources) == 1
        assert sources[0].type == "spotify"
        assert sources[0].external_id == "spotify:pixeluser"
        assert [event.type for event in events] == ["music_play", "music_play"]
        assert events[0].title == "Nova Echo - Starfall"
        assert events[0].timestamp_start == datetime(
            2024, 2, 1, 7, 14, 55, 667000, tzinfo=UTC
        )
        assert events[0].timestamp_end == datetime(2024, 2, 1, 7, 15, 10, tzinfo=UTC)
        assert events[0].raw_payload == {
            "username": "PixelUser",
            "platform": "android",
            "conn_country": "DE",
            "spotify_track_uri": "spotify:track:1234567890abcdef",
            "spotify_episode_uri": None,
            "shuffle": False,
            "skipped": False,
        }
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_spotify_ingestion_emits_shared_progress_snapshots() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    fixture_path = Path("test/assets/spotify_streaming_history_audio_test_fixture.json")
    document = workspace_root / "Streaming_History_Audio_2024.json"
    document.write_text(fixture_path.read_text(encoding="utf-8"), encoding="utf-8")
    snapshots = []

    try:
        result = SpotifyIngestionService().ingest(
            runtime=runtime,
            root=document,
            progress_callback=snapshots.append,
        )

        assert result.status == "completed"
        assert [
            snapshot.event for snapshot in snapshots if snapshot.event == "run_finished"
        ] == ["run_finished"]
        assert [
            snapshot.phase for snapshot in snapshots if snapshot.event == "phase_started"
        ] == [
            "filesystem discovery",
            "metadata extraction",
            "canonical persistence",
            "finalization",
        ]
        assert any(
            snapshot.event == "progress"
            and snapshot.phase == "filesystem discovery"
            and snapshot.completed == 1
            and snapshot.total == 1
            for snapshot in snapshots
        )
        assert any(
            snapshot.event == "progress"
            and snapshot.phase == "metadata extraction"
            and snapshot.completed == 1
            and snapshot.total == 1
            for snapshot in snapshots
        )
        assert any(
            snapshot.event == "progress"
            and snapshot.phase == "canonical persistence"
            and snapshot.completed == 1
            and snapshot.inserted == 2
            and snapshot.total == 1
            for snapshot in snapshots
        )
        assert snapshots[-1].event == "run_finished"
        assert snapshots[-1].phase == "finalization"
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def _create_runtime(*, spotify_root: Path | None = None):
    runtime = create_runtime_context(
        settings=Settings(database_url="sqlite://", spotify_root=spotify_root)
    )
    initialize_database(runtime)
    return runtime


def _create_workspace_root() -> Path:
    workspace_root = Path("var") / f"spotify-ingest-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=False)
    return workspace_root


def _build_spotify_document(rows: list[dict[str, object]]) -> str:
    return json.dumps(rows, indent=2)


def _spotify_row(
    *,
    ts: str,
    username: str,
    ms_played: int,
    track: str | None,
    shuffle: bool | None = False,
) -> dict[str, object]:
    return {
        "ts": ts,
        "username": username,
        "platform": "android",
        "ms_played": ms_played,
        "conn_country": "DE",
        "ip_addr_decrypted": "127.0.0.1",
        "user_agent_decrypted": "pytest",
        "master_metadata_track_name": track,
        "master_metadata_album_artist_name": "Artist" if track is not None else None,
        "master_metadata_album_album_name": "Album",
        "spotify_track_uri": (
            f"spotify:track:{track.casefold()}" if track is not None else None
        ),
        "episode_name": None,
        "episode_show_name": None,
        "spotify_episode_uri": None,
        "reason_start": "trackdone",
        "reason_end": "endplay",
        "shuffle": shuffle,
        "skipped": False,
        "offline": False,
        "offline_timestamp": None,
        "incognito_mode": False,
    }
