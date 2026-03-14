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
