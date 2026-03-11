# R-005 – Basic Timeline API Endpoint

## Goal

Expose a minimal API endpoint that returns time-ordered timeline entries
from both Events and Assets.

This establishes the unified timeline concept.

---

## Scope

Implement:

GET /timeline?start=...&end=...

Response should include:

- type ("event" | "asset")
- timestamp
- id
- summary/title (if available)
- coordinates (if available)

Combine:

- Event.timestamp_start
- Asset.timestamp

Return results ordered by timestamp ascending.

---

## Out of Scope

- No pagination (simple limit OK)
- No filtering by tag/person yet
- No aggregation
- No heatmap logic
- No authentication

---

## Acceptance Criteria

- Endpoint returns combined results
- Works with empty DB
- Works with only assets
- Works with only events
- Proper JSON schema via Pydantic

---

## Notes

This is a projection layer.
Do not modify domain model.
Do not create derived events for assets.