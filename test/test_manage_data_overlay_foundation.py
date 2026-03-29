"""Source-level regression checks for the manage-data overlay foundation."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT / "ui" / "src"


def test_top_bar_exposes_manage_action() -> None:
    source = (UI_ROOT / "app" / "layout" / "TopBar.tsx").read_text(
        encoding="utf-8"
    )

    assert "isManageDataOpen" in source
    assert "onToggleManageData" in source
    assert "Manage" in source
    assert "aria-pressed={isManageDataOpen}" in source


def test_app_shell_mounts_manage_data_overlay_with_local_state() -> None:
    source = (UI_ROOT / "app" / "AppShell.tsx").read_text(encoding="utf-8")

    assert "const [isManageDataOpen, setManageDataOpen] = useState(false);" in source
    assert "ManageDataOverlay" in source
    assert "isOpen={isManageDataOpen}" in source
    assert "onClose={() => setManageDataOpen(false)}" in source


def test_manage_overlay_tracks_drafts_and_guard_flow() -> None:
    source = (
        UI_ROOT / "features" / "manage-data" / "components" / "ManageDataOverlay.tsx"
    ).read_text(encoding="utf-8")

    assert "pendingGuardAction" in source
    assert "Discard changes" in source
    assert "Save changes" in source
    assert "Unsaved changes" in source
    assert "Save &amp; Close" in source
    assert "Switching sections or" in source


def test_manage_overlay_uses_shared_catalog_editor_primitives() -> None:
    source = (
        UI_ROOT
        / "features"
        / "manage-data"
        / "components"
        / "CatalogEditorPrimitives.tsx"
    ).read_text(encoding="utf-8")

    assert "CatalogSectionFrame" in source
    assert "CatalogTable" in source
    assert "CatalogLoadingState" in source
    assert "CatalogEmptyState" in source
    assert "CatalogErrorState" in source
