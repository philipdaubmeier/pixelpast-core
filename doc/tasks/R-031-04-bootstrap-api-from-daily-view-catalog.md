# R-031-04 - Bootstrap API from Daily View Catalog

## Goal

Switch the exploration bootstrap API so the list of available views is read
from `daily_view` instead of hard-coded provider definitions.

## Dependencies

- `R-024-01`
- `R-031-02`
- `R-031-03`
- `R-031`

## Scope

This task should complete the server-side transition to database-driven
exploration views.

### Read Path Direction

Introduce the repository and provider read behavior needed to:

- list all available `DailyView` rows
- expose their `id`, `label`, and `description` through the existing bootstrap
  response contract
- return the list in a stable deterministic order

The order matters because the UI now assigns view colors positionally.

### Provider Direction

The exploration/bootstrap provider should no longer depend on hard-coded view
definitions as the source of truth. If a fallback path is still temporarily
required for demo mode or empty databases, that fallback must be clearly
bounded and documented as transitional behavior.

### Validation Direction

Any server-side validation of requested `view_mode` values should resolve
against the `daily_view` catalog rather than against a hard-coded constant set.

## Out of Scope

- no redesign of the bootstrap response shape
- no custom sort controls for views yet
- no UI changes beyond consuming the unchanged bootstrap contract

## Acceptance Criteria

- bootstrap view metadata is read from `daily_view`
- bootstrap output order is stable and deterministic
- server-side `view_mode` validation no longer depends on hard-coded view ids
- hard-coded backend view definitions are removed or demoted to clearly bounded
  fallback/demo-only behavior

## Notes

Because the UI now colors views purely by bootstrap order, any ordering rule
introduced here becomes user-visible and should therefore be explicit and
stable.
