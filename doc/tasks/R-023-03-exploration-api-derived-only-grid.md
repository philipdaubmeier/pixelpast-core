# R-023-03 - Exploration API Derived-Only Grid

## Goal

Change the exploration and grid-facing API behavior so the day grid is sourced
only from derived daily aggregate data, while person and tag catalogs remain
loaded from canonical associations.

The current exploration bootstrap behavior mixes both layers by reading
canonical data when derived aggregates are missing. This task should remove that
fallback and make the API layering explicit.

## Dependencies

- `R-023-01`
- `R-023-02`
- `R-014`
- `R-015`

## Scope

### Remove Canonical Fallback for Grid Day Cells

Update the exploration/grid projection logic so day-cell counts, activity
scores, and presence/absence of grid data are read only from derived daily
aggregate rows.

If no derived row exists for a day, the grid-facing response must behave as a
true empty day rather than synthesizing values from canonical assets or events.

### Preserve Canonical Person and Tag Catalog Loading

The UI should continue to receive person and tag catalogs from canonical
associations.

This task must preserve that behavior explicitly for:

- visible person catalogs
- visible tag catalogs
- canonical label resolution for those catalogs

The API should not force person and tag catalogs through the derived layer as
part of this task.

### Define Connector-Aware Exploration Projections

Adapt the exploration API contract so it can consume the revised connector-aware
daily aggregate model.

This includes deciding how the API exposes:

- overall per-day grid state
- connector-specific daily projections when needed later
- derived semantic summaries attached to a day aggregate

The immediate requirement is that the primary day grid becomes derived-only, but
the response design should not block future connector-level views.

### Review Day Context Boundaries

This task should explicitly decide which parts of day-context and hover-context
remain canonical for now and which, if any, move to derived tables.

At minimum, the task must document that:

- person and tag catalogs remain canonical
- the day grid becomes derived-only
- any remaining canonical day-context reads are intentional and temporary if
  they are kept

### Update API and Integration Tests

Tests must be updated so they verify the corrected layering.

At minimum, coverage should assert:

- after ingest without derive, the grid shows no day data
- after derive, the grid shows data based on daily aggregates
- person and tag catalogs still load from canonical links
- mixed-source derived days are surfaced correctly in the exploration response

## Out of Scope

- no UI redesign
- no change to canonical tag/person ingestion behavior
- no requirement to move every day-detail endpoint to derived data

## Acceptance Criteria

- the exploration/grid API no longer synthesizes day-cell values from canonical
  events or assets when derived rows are absent
- person and tag catalogs remain available from canonical associations
- the API contract is compatible with connector-aware daily aggregates
- tests explicitly cover the case of ingest-without-derive resulting in an
  empty grid
- the resulting API behavior aligns with strict `Raw -> Canonical -> Derived`
  layering for day-grid rendering

## Notes

This task is intentionally narrower than a full exploration read-model rewrite.
Its purpose is to correct the current architectural leak where the grid behaves
as if derivation had already happened when it has not.
