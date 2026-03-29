"""Unit tests for the shared persistence outcome summary wire contract."""

from pixelpast.shared.persistence_outcome_summary import PersistenceOutcomeSummary


def test_persistence_outcome_summary_serializes_event_summary_with_existing_field_order(
) -> None:
    summary = PersistenceOutcomeSummary(
        inserted=1,
        updated=2,
        unchanged=3,
        missing_from_source=4,
        skipped=5,
        persisted_event_count=6,
    )

    assert (
        summary.to_wire()
        == "inserted=1;updated=2;unchanged=3;missing_from_source=4;skipped=5;"
        "persisted_event_count=6"
    )


def test_persistence_outcome_summary_serializes_asset_summary_with_existing_field_order(
) -> None:
    summary = PersistenceOutcomeSummary(
        inserted=1,
        updated=0,
        unchanged=2,
        missing_from_source=3,
        skipped=0,
        persisted_asset_count=4,
        included_fields=frozenset({"missing_from_source"}),
    )

    assert (
        summary.to_wire()
        == "inserted=1;updated=0;unchanged=2;missing_from_source=3;skipped=0;"
        "persisted_asset_count=4"
    )


def test_persistence_outcome_summary_parses_detailed_wire_format() -> None:
    summary = PersistenceOutcomeSummary.parse(
        "inserted=1;updated=2;unchanged=3;missing_from_source=4;skipped=5;"
        "persisted_event_count=6"
    )

    assert summary.is_detailed is True
    assert summary.inserted == 1
    assert summary.updated == 2
    assert summary.unchanged == 3
    assert summary.missing_from_source == 4
    assert summary.skipped == 5
    assert summary.persisted_event_count == 6


def test_persistence_outcome_summary_parses_legacy_simple_wire_format() -> None:
    summary = PersistenceOutcomeSummary.parse("updated:2")

    assert summary.is_detailed is False
    assert summary.simple_outcome == "updated"
    assert summary.persisted_event_count == 2
    assert summary.to_wire() == "updated:2"


def test_persistence_outcome_summary_can_force_zero_valued_fields_into_wire_output() -> (
    None
):
    summary = PersistenceOutcomeSummary(
        inserted=0,
        updated=0,
        unchanged=3,
        skipped=0,
        missing_from_source=0,
        persisted_asset_count=3,
        included_fields=frozenset({"missing_from_source"}),
    )

    assert (
        summary.to_wire()
        == "inserted=0;updated=0;unchanged=3;missing_from_source=0;skipped=0;"
        "persisted_asset_count=3"
    )
