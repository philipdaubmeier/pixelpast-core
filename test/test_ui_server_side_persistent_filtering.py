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
    assert "`/days/context${buildQueryString({" in source


def test_timeline_transport_builds_day_context_query_from_persistent_filters() -> None:
    source = (UI_ROOT / "api" / "timelineTransport.ts").read_text(encoding="utf-8")

    assert "view_mode: request.viewMode" in source
    assert "person_ids: request.personIds" in source
    assert "tag_paths: request.tagPaths" in source


def test_app_bootstrap_separates_bootstrap_and_grid_loading() -> None:
    source = (UI_ROOT / "app" / "App.tsx").read_text(encoding="utf-8")

    assert "timelineApi.getExplorationBootstrap()" in source
    assert "timelineApi.getExplorationGrid(explorationRange, {" in source
    assert "latestGridRequestIdRef" in source
    assert "setGridState(\"loading\")" in source


def test_app_bootstrap_resets_hover_context_when_persistent_scope_changes() -> None:
    source = (UI_ROOT / "app" / "App.tsx").read_text(encoding="utf-8")

    assert "latestDayContextScopeRef" in source
    assert "setDayContextsByDate({})" in source
    assert "setLoadedDayContextRanges([])" in source
    assert "setLoadingDayContextRanges([])" in source
    assert "setFailedDayContextRanges([])" in source


def test_exploration_projection_uses_server_grid_as_source_of_truth() -> None:
    source = (UI_ROOT / "projections" / "exploration.ts").read_text(
        encoding="utf-8"
    )

    assert "renderColorValue: day.color" in source
    assert "matchingDayCount = gridDays.filter((day) => day.color !== \"empty\").length" in source
    assert "function matchesPersistentFilters(" not in source
    assert "function getViewModeColorValue(" not in source


def test_timeline_api_maps_grid_contract_with_backend_count() -> None:
    source = (UI_ROOT / "api" / "timeline.ts").read_text(encoding="utf-8")

    assert "count: day.count" in source
    assert "color: day.color" in source
    assert "label: day.label" in source
    assert "activityScore: day.activity_score" not in source
    assert "eventCount: 0" not in source
    assert "assetCount: 0" not in source
    assert "personIds: []" not in source
    assert "tagPaths: []" not in source


def test_heatmap_day_projection_no_longer_carries_client_filter_arrays() -> None:
    source = (UI_ROOT / "projections" / "timeline.ts").read_text(encoding="utf-8")

    assert "personIds:" not in source
    assert "tagPaths:" not in source
    assert "count:" in source
    assert "activityScore:" not in source
    assert "hasData:" not in source


def test_day_cell_supports_direct_hex_colors_and_backend_count_tooltip() -> None:
    source = (UI_ROOT / "features" / "timeline" / "components" / "DayCell.tsx").read_text(
        encoding="utf-8"
    )

    assert "colorValue.startsWith(\"#\")" in source
    assert "backgroundColor: colorValue" in source
    assert "`${day.count} items`" in source
