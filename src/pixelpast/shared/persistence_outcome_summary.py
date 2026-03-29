"""Shared internal serializer/parser for ingestion persistence outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field

_DETAILED_FIELD_ORDER = (
    "inserted",
    "updated",
    "unchanged",
    "missing_from_source",
    "skipped",
    "failed",
    "persisted_event_count",
    "persisted_asset_count",
)


@dataclass(frozen=True, slots=True)
class PersistenceOutcomeSummary:
    """Internal value object for persistence outcome wire summaries."""

    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed: int = 0
    missing_from_source: int = 0
    persisted_event_count: int = 0
    persisted_asset_count: int = 0
    simple_outcome: str | None = None
    included_fields: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def parse(cls, outcome: str) -> PersistenceOutcomeSummary:
        """Parse either the legacy simple outcome or detailed summary wire format."""

        if "=" in outcome and ";" in outcome:
            detailed_counts = {
                key: int(value)
                for key, value in (
                    part.split("=", 1) for part in outcome.split(";") if part.strip()
                )
            }
            return cls(
                inserted=detailed_counts.get("inserted", 0),
                updated=detailed_counts.get("updated", 0),
                unchanged=detailed_counts.get("unchanged", 0),
                skipped=detailed_counts.get("skipped", 0),
                failed=detailed_counts.get("failed", 0),
                missing_from_source=detailed_counts.get("missing_from_source", 0),
                persisted_event_count=detailed_counts.get("persisted_event_count", 0),
                persisted_asset_count=detailed_counts.get("persisted_asset_count", 0),
            )

        normalized_outcome, separator, persisted_count = outcome.partition(":")
        if not separator:
            return cls(simple_outcome=normalized_outcome)

        parsed_count = int(persisted_count)
        return cls(
            simple_outcome=normalized_outcome,
            persisted_event_count=parsed_count,
        )

    @property
    def is_detailed(self) -> bool:
        return self.simple_outcome is None

    def to_wire(self) -> str:
        """Serialize the summary to the existing deterministic wire format."""

        if self.simple_outcome is not None:
            persisted_count = self.persisted_event_count or self.persisted_asset_count
            if persisted_count:
                return f"{self.simple_outcome}:{persisted_count}"
            return self.simple_outcome

        values = {
            "inserted": self.inserted,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "missing_from_source": self.missing_from_source,
            "skipped": self.skipped,
            "failed": self.failed,
            "persisted_event_count": self.persisted_event_count,
            "persisted_asset_count": self.persisted_asset_count,
        }
        parts = [
            f"{field}={values[field]}"
            for field in _DETAILED_FIELD_ORDER
            if field in self._included_fields(values=values)
        ]
        return ";".join(parts)

    def _included_fields(self, *, values: dict[str, int]) -> set[str]:
        included = {
            field
            for field in _DETAILED_FIELD_ORDER
            if values[field] != 0
            or field in {"inserted", "updated", "unchanged", "skipped"}
            or field in self.included_fields
        }
        if values["persisted_event_count"] != 0 or "persisted_event_count" in self.included_fields:
            included.add("persisted_event_count")
        if values["persisted_asset_count"] != 0 or "persisted_asset_count" in self.included_fields:
            included.add("persisted_asset_count")
        if values["missing_from_source"] != 0 or "missing_from_source" in self.included_fields:
            included.add("missing_from_source")
        if values["failed"] != 0 or "failed" in self.included_fields:
            included.add("failed")
        return included


__all__ = ["PersistenceOutcomeSummary"]
