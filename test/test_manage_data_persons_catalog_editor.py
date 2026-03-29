"""Source-level regression checks for the manage-data persons catalog editor."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT / "ui" / "src"


def test_manage_data_client_maps_persons_catalog_to_real_api_contract() -> None:
    source = (
        UI_ROOT / "features" / "manage-data" / "client.ts"
    ).read_text(encoding="utf-8")

    assert "manageDataTransport.getPersonsCatalog()" in source
    assert "manageDataTransport.savePersonsCatalog" in source
    assert "path: person.path ?? \"\"" in source
    assert "delete_ids: []" in source
    assert "id: toPersistedIdentifier(row.id)" in source


def test_manage_data_overlay_renders_persons_editor_with_inline_search_and_creation() -> None:
    source = (
        UI_ROOT / "features" / "manage-data" / "components" / "ManageDataOverlay.tsx"
    ).read_text(encoding="utf-8")

    assert "title=\"Persons\"" in source
    assert "searchPlaceholder=\"Search name, aliases, or path\"" in source
    assert "addLabel=\"+ Add person\"" in source
    assert "Comma-separated aliases" in source
    assert "Deletion intentionally unavailable in v1." in source


def test_manage_data_overlay_reloads_section_after_successful_save() -> None:
    source = (
        UI_ROOT / "features" / "manage-data" / "components" / "ManageDataOverlay.tsx"
    ).read_text(encoding="utf-8")

    assert "await saveSectionData(activeSectionId, draftRows);" in source
    assert "const reloadedRows = await loadSectionData(activeSectionId);" in source
    assert "snapshot: cloneSectionRows(reloadedRows)" in source
    assert "draft: cloneSectionRows(reloadedRows)" in source
