# R-026 - Remove Legacy Heatmap API

## Goal

Remove the legacy `GET /heatmap` API and all code that exists only to support
it.

The exploration UI no longer calls this endpoint and now uses the split
exploration contracts instead. This task should eliminate the remaining
low-level heatmap route, service logic, read repository surface, tests, and
documentation so the timeline API has one clear grid-facing path.

## Dependencies

- `R-024-01`
- `R-024-02`

## Reasoning

The current codebase still carries two different derived day-grid reads:

- `GET /heatmap`
- `GET /exploration`

Only the exploration endpoint is used by the current UI. Keeping the legacy
heatmap contract alongside it creates avoidable overlap in:

- route surface
- service and repository wiring
- integration tests
- API documentation
- maintenance and refactor cost

This task is not about replacing the current exploration contract. It is about
removing the older parallel path now that the UI and architecture have moved to
the split exploration model.

## Scope

### Remove the Heatmap Route and Schema Contract

Delete the `GET /heatmap` endpoint and the dedicated Pydantic schema types that
exist only for that route.

This includes removing:

- the route handler
- the request validation logic specific to that route
- `HeatmapDay`
- `HeatmapResponse`

### Remove Service-Layer Support That Exists Only for Heatmap Reads

Delete the service code that composes the heatmap response.

If the timeline query service is left with responsibilities that no longer
justify its existence, this task should either simplify it or remove the unused
parts explicitly rather than leaving dead abstractions behind.

### Remove Read-Repository Surface That Exists Only for Heatmap

Delete any read repository methods and supporting snapshot structures that are
used only by the removed heatmap API.

This includes reviewing:

- `DailyAggregateReadRepository`
- heatmap-specific snapshot models
- dependency wiring that exists only for the removed route

Shared derived reads that are still required by `/exploration` should remain in
place. The task must distinguish clearly between:

- derived reads still needed for exploration range/grid behavior
- derived reads that exist only because `/heatmap` still exists

### Remove Heatmap-Specific Tests

Delete or rewrite tests so the suite no longer expects the legacy route or its
supporting contract.

At minimum, remove coverage for:

- empty heatmap ranges
- ordered heatmap responses
- overall-row-only heatmap behavior
- invalid heatmap range handling

Tests that still matter architecturally should be preserved by moving their
intent to the exploration endpoint where appropriate.

### Remove Documentation and References

Update project documentation so `/heatmap` is no longer presented as a supported
API.

This includes reviewing:

- task documents
- README or architecture docs
- comments and module docstrings
- developer-facing references in code or tests

Historical task files do not need to be rewritten as if the endpoint never
existed, but any current-state documentation should stop describing it as an
active API.

## Out of Scope

- no redesign of the exploration endpoint
- no change to the day-detail endpoint unless cleanup requires minor wiring
  adjustments
- no new analytics features
- no replacement compatibility shim for `/heatmap`

## Acceptance Criteria

- `GET /heatmap` is removed from the API surface
- heatmap-specific Pydantic schema models are removed
- service and repository code that existed only for the heatmap API is removed
  or simplified away
- tests no longer reference or expect the legacy heatmap endpoint
- current-state documentation no longer lists `/heatmap` as a supported API
- the remaining exploration and day-detail APIs continue to pass their tests

## Notes

This task should prefer complete removal over deprecation scaffolding. The
endpoint is already unused by the UI, so the desired outcome is a smaller and
clearer read stack rather than one more compatibility layer to maintain.
