"""Characterization tests for Spotify ingestion contracts and fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pixelpast.ingestion.spotify import (
    LoadedSpotifyStreamingHistoryDocument,
    ParsedSpotifyStreamingHistoryDocument,
    ParsedSpotifyStreamRow,
    SpotifyAccountSourceCandidate,
    SpotifyDocumentCandidate,
    SpotifyEventCandidate,
    SpotifyIngestionResult,
    SpotifyStreamingHistoryDocumentDescriptor,
    SpotifyTransformError,
    build_spotify_account_source_candidates,
    build_spotify_document_candidate,
    build_spotify_event_candidates,
    build_spotify_event_candidates_for_documents,
    parse_loaded_spotify_streaming_history_document,
    parse_spotify_streaming_history_document,
)
from pixelpast.ingestion.spotify import contracts as spotify_contracts


def test_spotify_ingest_public_contract_imports_remain_stable() -> None:
    assert (
        SpotifyStreamingHistoryDocumentDescriptor
        is spotify_contracts.SpotifyStreamingHistoryDocumentDescriptor
    )
    assert (
        LoadedSpotifyStreamingHistoryDocument
        is spotify_contracts.LoadedSpotifyStreamingHistoryDocument
    )
    assert ParsedSpotifyStreamingHistoryDocument is (
        spotify_contracts.ParsedSpotifyStreamingHistoryDocument
    )
    assert ParsedSpotifyStreamRow is spotify_contracts.ParsedSpotifyStreamRow
    assert SpotifyAccountSourceCandidate is (
        spotify_contracts.SpotifyAccountSourceCandidate
    )
    assert SpotifyDocumentCandidate is spotify_contracts.SpotifyDocumentCandidate
    assert SpotifyEventCandidate is spotify_contracts.SpotifyEventCandidate
    assert SpotifyTransformError is spotify_contracts.SpotifyTransformError
    assert SpotifyIngestionResult is spotify_contracts.SpotifyIngestionResult


def test_spotify_fixture_characterizes_track_and_episode_rows() -> None:
    fixture_path = Path("test/assets/spotify_streaming_history_audio_test_fixture.json")
    descriptor = SpotifyStreamingHistoryDocumentDescriptor(path=fixture_path)

    parsed = parse_spotify_streaming_history_document(
        descriptor=descriptor,
        text=fixture_path.read_text(encoding="utf-8"),
    )
    source_candidates = build_spotify_account_source_candidates([parsed])
    event_candidates = build_spotify_event_candidates(parsed)

    assert parsed.descriptor.origin_label == fixture_path.resolve().as_posix()
    assert len(parsed.rows) == 2

    track_row = parsed.rows[0]
    assert track_row.row_index == 0
    assert track_row.document_origin_label == fixture_path.resolve().as_posix()
    assert track_row.timestamp_end == datetime(2024, 2, 1, 7, 15, 10, tzinfo=UTC)
    assert track_row.ms_played == 14333
    assert track_row.master_metadata_album_artist_name == "Nova Echo"
    assert track_row.master_metadata_track_name == "Starfall"
    assert track_row.spotify_track_uri == "spotify:track:1234567890abcdef"
    assert track_row.spotify_episode_uri is None

    episode_row = parsed.rows[1]
    assert episode_row.username == "pixeluser"
    assert episode_row.normalized_username == "pixeluser"
    assert episode_row.master_metadata_album_artist_name is None
    assert episode_row.master_metadata_track_name is None
    assert episode_row.spotify_track_uri is None
    assert episode_row.spotify_episode_uri == "spotify:episode:abcdef1234567890"

    assert source_candidates == (
        SpotifyAccountSourceCandidate(
            type="spotify",
            name="pixeluser",
            external_id="spotify:pixeluser",
            config_json={
                "username": "pixeluser",
                "origin_labels": [fixture_path.resolve().as_posix()],
            },
        ),
    )

    assert len(event_candidates) == 2
    assert event_candidates[0] == SpotifyEventCandidate(
        source_external_id="spotify:pixeluser",
        external_event_id=None,
        type="music_play",
        timestamp_start=datetime(2024, 2, 1, 7, 14, 55, 667000, tzinfo=UTC),
        timestamp_end=datetime(2024, 2, 1, 7, 15, 10, tzinfo=UTC),
        title="Nova Echo - Starfall",
        summary=None,
        raw_payload={
            "username": "PixelUser",
            "platform": "android",
            "conn_country": "DE",
            "spotify_track_uri": "spotify:track:1234567890abcdef",
            "spotify_episode_uri": None,
            "shuffle": False,
            "skipped": False,
        },
        derived_payload=None,
    )
    assert event_candidates[1].title == ""
    assert event_candidates[1].timestamp_start == datetime(
        2024,
        2,
        1,
        7,
        54,
        55,
        tzinfo=UTC,
    )
    assert event_candidates[1].raw_payload["username"] == "pixeluser"


def test_spotify_title_remains_empty_when_artist_or_track_is_unavailable() -> None:
    fixture_path = Path(
        "test/assets/spotify_streaming_history_audio_missing_title_fixture.json"
    )

    parsed = parse_spotify_streaming_history_document(
        descriptor=SpotifyStreamingHistoryDocumentDescriptor(path=fixture_path),
        text=fixture_path.read_text(encoding="utf-8"),
    )

    candidate = build_spotify_event_candidates(parsed)[0]

    assert candidate.title == ""
    assert candidate.summary is None


def test_spotify_document_candidate_makes_multi_username_documents_explicit() -> None:
    descriptor = SpotifyStreamingHistoryDocumentDescriptor(path=Path("mixed.json"))
    parsed = parse_spotify_streaming_history_document(
        descriptor=descriptor,
        text=(
            "["
            "{\"ts\":\"2024-02-01T08:00:00Z\",\"username\":\"SecondUser\","
            "\"platform\":\"web\",\"ms_played\":2000,\"conn_country\":\"DE\","
            "\"master_metadata_track_name\":\"Two\","
            "\"master_metadata_album_artist_name\":\"Artist\","
            "\"spotify_track_uri\":\"spotify:track:2\","
            "\"episode_name\":null,\"episode_show_name\":null,"
            "\"spotify_episode_uri\":null,\"shuffle\":null,\"skipped\":true},"
            "{\"ts\":\"2024-02-01T07:15:10Z\",\"username\":\"PixelUser\","
            "\"platform\":\"android\",\"ms_played\":1000,\"conn_country\":\"DE\","
            "\"master_metadata_track_name\":\"One\","
            "\"master_metadata_album_artist_name\":\"Artist\","
            "\"spotify_track_uri\":\"spotify:track:1\","
            "\"episode_name\":null,\"episode_show_name\":null,"
            "\"spotify_episode_uri\":null,\"shuffle\":false,\"skipped\":false}"
            "]"
        ),
    )

    candidate = build_spotify_document_candidate(parsed)

    assert candidate == SpotifyDocumentCandidate(
        document=descriptor,
        rows=parsed.rows,
        source_candidates=(
            SpotifyAccountSourceCandidate(
                type="spotify",
                name="pixeluser",
                external_id="spotify:pixeluser",
                config_json={
                    "username": "pixeluser",
                    "origin_labels": [descriptor.origin_label],
                },
            ),
            SpotifyAccountSourceCandidate(
                type="spotify",
                name="seconduser",
                external_id="spotify:seconduser",
                config_json={
                    "username": "seconduser",
                    "origin_labels": [descriptor.origin_label],
                },
            ),
        ),
        events=(
            SpotifyEventCandidate(
                source_external_id="spotify:pixeluser",
                external_event_id=None,
                type="music_play",
                timestamp_start=datetime(2024, 2, 1, 7, 15, 9, tzinfo=UTC),
                timestamp_end=datetime(2024, 2, 1, 7, 15, 10, tzinfo=UTC),
                title="Artist - One",
                summary=None,
                raw_payload={
                    "username": "PixelUser",
                    "platform": "android",
                    "conn_country": "DE",
                    "spotify_track_uri": "spotify:track:1",
                    "spotify_episode_uri": None,
                    "shuffle": False,
                    "skipped": False,
                },
                derived_payload=None,
            ),
            SpotifyEventCandidate(
                source_external_id="spotify:seconduser",
                external_event_id=None,
                type="music_play",
                timestamp_start=datetime(2024, 2, 1, 7, 59, 58, tzinfo=UTC),
                timestamp_end=datetime(2024, 2, 1, 8, 0, 0, tzinfo=UTC),
                title="Artist - Two",
                summary=None,
                raw_payload={
                    "username": "SecondUser",
                    "platform": "web",
                    "conn_country": "DE",
                    "spotify_track_uri": "spotify:track:2",
                    "spotify_episode_uri": None,
                    "shuffle": None,
                    "skipped": True,
                },
                derived_payload=None,
            ),
        ),
    )


def test_spotify_account_identity_groups_rows_by_normalized_username() -> None:
    first_document = parse_spotify_streaming_history_document(
        descriptor=SpotifyStreamingHistoryDocumentDescriptor(
            path=Path("first.json"),
        ),
        text=(
            "["
            "{\"ts\":\"2024-02-01T07:15:10Z\",\"username\":\"PixelUser\","
            "\"platform\":\"android\",\"ms_played\":1000,\"conn_country\":\"DE\","
            "\"master_metadata_track_name\":\"One\","
            "\"master_metadata_album_artist_name\":\"Artist\","
            "\"spotify_track_uri\":\"spotify:track:1\","
            "\"episode_name\":null,\"episode_show_name\":null,"
            "\"spotify_episode_uri\":null,\"shuffle\":false,\"skipped\":false}"
            "]"
        ),
    )
    second_document = parse_loaded_spotify_streaming_history_document(
        LoadedSpotifyStreamingHistoryDocument(
            descriptor=SpotifyStreamingHistoryDocumentDescriptor(
                path=Path("second.json"),
            ),
            text=(
                "["
                "{\"ts\":\"2024-02-01T08:00:00Z\",\"username\":\" pixeluser \","
                "\"platform\":\"web\",\"ms_played\":2000,\"conn_country\":\"DE\","
                "\"master_metadata_track_name\":\"Two\","
                "\"master_metadata_album_artist_name\":\"Artist\","
                "\"spotify_track_uri\":\"spotify:track:2\","
                "\"episode_name\":null,\"episode_show_name\":null,"
                "\"spotify_episode_uri\":null,\"shuffle\":null,\"skipped\":true}"
                "]"
            ),
        )
    )

    candidates = build_spotify_account_source_candidates(
        [first_document, second_document]
    )

    assert candidates == (
        SpotifyAccountSourceCandidate(
            type="spotify",
            name="pixeluser",
            external_id="spotify:pixeluser",
            config_json={
                "username": "pixeluser",
                "origin_labels": sorted(
                    [
                        Path("first.json").resolve().as_posix(),
                        Path("second.json").resolve().as_posix(),
                    ]
                ),
            },
        ),
    )


def test_spotify_event_candidates_are_sorted_deterministically_across_documents() -> None:
    later_path = Path("z-last.json")
    earlier_path = Path("a-first.json")
    later_document = parse_spotify_streaming_history_document(
        descriptor=SpotifyStreamingHistoryDocumentDescriptor(path=later_path),
        text=(
            "["
            "{\"ts\":\"2024-02-01T08:00:00Z\",\"username\":\"PixelUser\","
            "\"platform\":\"web\",\"ms_played\":1000,\"conn_country\":\"DE\","
            "\"master_metadata_track_name\":\"Later\","
            "\"master_metadata_album_artist_name\":\"Artist\","
            "\"spotify_track_uri\":\"spotify:track:later\","
            "\"episode_name\":null,\"episode_show_name\":null,"
            "\"spotify_episode_uri\":null,\"shuffle\":false,\"skipped\":false},"
            "{\"ts\":\"2024-02-01T07:00:00Z\",\"username\":\"PixelUser\","
            "\"platform\":\"web\",\"ms_played\":1000,\"conn_country\":\"DE\","
            "\"master_metadata_track_name\":\"Second\","
            "\"master_metadata_album_artist_name\":\"Artist\","
            "\"spotify_track_uri\":\"spotify:track:second\","
            "\"episode_name\":null,\"episode_show_name\":null,"
            "\"spotify_episode_uri\":null,\"shuffle\":false,\"skipped\":false}"
            "]"
        ),
    )
    earlier_document = parse_spotify_streaming_history_document(
        descriptor=SpotifyStreamingHistoryDocumentDescriptor(path=earlier_path),
        text=(
            "["
            "{\"ts\":\"2024-02-01T07:00:00Z\",\"username\":\" pixeluser \","
            "\"platform\":\"android\",\"ms_played\":1000,\"conn_country\":\"DE\","
            "\"master_metadata_track_name\":\"First\","
            "\"master_metadata_album_artist_name\":\"Artist\","
            "\"spotify_track_uri\":\"spotify:track:first\","
            "\"episode_name\":null,\"episode_show_name\":null,"
            "\"spotify_episode_uri\":null,\"shuffle\":true,\"skipped\":false}"
            "]"
        ),
    )

    candidates = build_spotify_event_candidates_for_documents(
        [later_document, earlier_document]
    )

    assert [candidate.title for candidate in candidates] == [
        "Artist - First",
        "Artist - Second",
        "Artist - Later",
    ]


def test_spotify_parser_rejects_non_array_documents() -> None:
    descriptor = SpotifyStreamingHistoryDocumentDescriptor(path=Path("invalid.json"))

    try:
        parse_spotify_streaming_history_document(
            descriptor=descriptor,
            text="{\"ts\": \"2024-02-01T07:15:10Z\"}",
        )
    except ValueError as error:
        assert str(error) == (
            "Spotify streaming-history document must contain a top-level JSON array: "
            f"{descriptor.origin_label}"
        )
    else:
        raise AssertionError("Expected non-array Spotify document to fail.")


def test_spotify_parser_rejects_rows_without_username() -> None:
    descriptor = SpotifyStreamingHistoryDocumentDescriptor(path=Path("invalid.json"))

    try:
        parse_spotify_streaming_history_document(
            descriptor=descriptor,
            text=(
                "["
                "{\"ts\":\"2024-02-01T07:15:10Z\",\"username\":\" \","
                "\"platform\":\"android\",\"ms_played\":1000,\"conn_country\":\"DE\","
                "\"master_metadata_track_name\":\"One\","
                "\"master_metadata_album_artist_name\":\"Artist\","
                "\"spotify_track_uri\":\"spotify:track:1\","
                "\"episode_name\":null,\"episode_show_name\":null,"
                "\"spotify_episode_uri\":null,\"shuffle\":false,\"skipped\":false}"
                "]"
            ),
        )
    except ValueError as error:
        assert str(error) == (
            "Spotify streaming-history row is missing a valid 'username' value."
        )
    else:
        raise AssertionError("Expected blank Spotify username to fail.")
