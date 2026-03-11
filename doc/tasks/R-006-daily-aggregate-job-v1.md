# R-006 - Daily Aggregate Job v1

## Goal

Implement the first derived-layer job that converts canonical temporal data into
day-level summaries.

This task is the first direct step toward the product's heatmap-centric user
experience.

---

## Scope

Implement:

- a derived job entrypoint for `daily-aggregate`
- day-level aggregation over canonical `Event` and `Asset` data
- a persistence shape for `DailyAggregate`
- repeatable re-computation for a requested date range or full rebuild

Include, at minimum:

- `date`
- `total_events`
- `media_count`
- `activity_score`

Document the initial scoring approach clearly, even if it is intentionally
simple.

---

## Out of Scope

- No complex cross-source inference
- No trip or vacation detection
- No UI
- No advanced scoring heuristics

---

## Acceptance Criteria

- derive job runs via CLI
- job is repeatable and idempotent
- output is generated from canonical data only
- empty datasets are handled correctly
- tests cover recomputation behavior

---

## Notes

Keep strict `Raw -> Canonical -> Derived` separation.
This job should not contain ingestion logic.
