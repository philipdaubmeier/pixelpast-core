"""Frontend workspace structure checks."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT / "ui"


def test_ui_workspace_contains_expected_files() -> None:
    expected_paths = [
        UI_ROOT / "package.json",
        UI_ROOT / "vite.config.ts",
        UI_ROOT / "tailwind.config.ts",
        UI_ROOT / "src" / "app" / "App.tsx",
        UI_ROOT / "src" / "app" / "AppShell.tsx",
        UI_ROOT / "src" / "app" / "layout" / "TopBar.tsx",
        UI_ROOT / "src" / "app" / "layout" / "MainSplitLayout.tsx",
        UI_ROOT / "src" / "app" / "layout" / "LeftGridPane.tsx",
        UI_ROOT / "src" / "app" / "layout" / "RightContextPane.tsx",
        UI_ROOT
        / "src"
        / "features"
        / "context"
        / "components"
        / "PersonsPanel.tsx",
        UI_ROOT
        / "src"
        / "features"
        / "context"
        / "components"
        / "TagsPanel.tsx",
        UI_ROOT / "src" / "features" / "context" / "components" / "MapPanel.tsx",
        UI_ROOT / "src" / "api" / "timeline.ts",
        UI_ROOT / "src" / "projections" / "timeline.ts",
        UI_ROOT / "src" / "state" / "UiStateContext.tsx",
        UI_ROOT / "src" / "mocks" / "timeline.ts",
    ]

    missing_paths = [path for path in expected_paths if not path.exists()]

    assert missing_paths == []


def test_ui_package_json_exposes_bootstrap_scripts() -> None:
    package_json = json.loads((UI_ROOT / "package.json").read_text(encoding="utf-8"))

    assert package_json["name"] == "pixelpast-ui"
    assert package_json["scripts"]["dev"] == "vite"
    assert package_json["scripts"]["build"] == "tsc -b && vite build"
