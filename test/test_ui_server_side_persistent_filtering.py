"""Source-level regression checks for server-side persistent grid filtering."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT / "ui" / "src"


def test_timeline_transport_builds_server_side_filter_query() -> None:
    source = (UI_ROOT / "api" / "timelineTransport.ts").read_text(encoding="utf-8")

    assert "view_mode: request.viewMode" in source
    assert "person_ids: request.personIds" in source
    assert "tag_paths: request.tagPaths" in source
    assert "location_geometry: request.locationGeometry" in source
    assert "filename_query: request.filenameQuery" in source


def test_app_bootstrap_separates_bootstrap_and_grid_loading() -> None:
    source = (UI_ROOT / "app" / "App.tsx").read_text(encoding="utf-8")

    assert "timelineApi.getExplorationBootstrap()" in source
    assert "timelineApi.getExplorationGrid(explorationRange, {" in source
    assert "latestGridRequestIdRef" in source
    assert "setGridState(\"loading\")" in source


def test_exploration_projection_uses_server_grid_as_source_of_truth() -> None:
    source = (UI_ROOT / "projections" / "exploration.ts").read_text(
        encoding="utf-8"
    )

    assert "renderColorValue: day.colorValue" in source
    assert "matchingDayCount = gridDays.filter((day) => day.hasData).length" in source
    assert "function matchesPersistentFilters(" not in source
    assert "function getViewModeColorValue(" not in source


def test_timeline_api_maps_grid_count_without_legacy_placeholders() -> None:
    source = (UI_ROOT / "api" / "timeline.ts").read_text(encoding="utf-8")

    assert "count: day.count" in source
    assert "eventCount: 0" not in source
    assert "assetCount: 0" not in source
    assert "personIds: []" not in source
    assert "tagPaths: []" not in source


def test_heatmap_day_projection_no_longer_carries_client_filter_arrays() -> None:
    source = (UI_ROOT / "projections" / "timeline.ts").read_text(encoding="utf-8")

    assert "personIds:" not in source
    assert "tagPaths:" not in source


def test_day_cell_tooltip_uses_backend_count() -> None:
    source = (UI_ROOT / "features" / "timeline" / "components" / "DayCell.tsx").read_text(
        encoding="utf-8"
    )

    assert "`${day.count} items`" in source
    assert "eventCount" not in source
    assert "assetCount" not in source
