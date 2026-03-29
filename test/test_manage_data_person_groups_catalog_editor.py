"""Source-level regression checks for the manage-data person-groups editor."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT / "ui" / "src"


def test_manage_data_client_maps_person_groups_catalog_and_delete_contract() -> None:
    source = (
        UI_ROOT / "features" / "manage-data" / "client.ts"
    ).read_text(encoding="utf-8")

    assert "manageDataTransport.getPersonGroupsCatalog()" in source
    assert "manageDataTransport.savePersonGroupsCatalog" in source
    assert "memberCount: group.member_count" in source
    assert "delete_ids: deleteIds" in source


def test_manage_data_overlay_renders_person_groups_editor_actions() -> None:
    source = (
        UI_ROOT / "features" / "manage-data" / "components" / "ManageDataOverlay.tsx"
    ).read_text(encoding="utf-8")

    assert 'title="Person Groups"' in source
    assert 'searchPlaceholder="Search group name"' in source
    assert 'addLabel="+ Add group"' in source
    assert "Manage members" in source
    assert "Delete group" in source
    assert "Confirm delete" in source


def test_manage_data_overlay_preserves_membership_subview_context() -> None:
    source = (
        UI_ROOT / "features" / "manage-data" / "components" / "ManageDataOverlay.tsx"
    ).read_text(encoding="utf-8")

    assert "activePersonGroupMembershipRowId" in source
    assert "Person Group Membership" in source
    assert "Back to catalog" in source
    assert "selected person group in focus" in source
