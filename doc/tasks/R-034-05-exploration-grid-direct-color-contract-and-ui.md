# R-034-05 - Exploration Grid Direct-Color Contract and UI

## Goal

Reshape the exploration grid API contract and the consuming UI so day cells can
be rendered from either existing color tokens or direct per-day hex colors,
without introducing a separate `color_mode` transport field.

This task should also remove per-day fields from the grid response that are no
longer needed by the current UI.

## Dependencies

- `R-034-04`
- `R-034`

## Scope

### API Contract Direction

Replace the current per-day exploration payload shape with a leaner contract.

The target payload for one day is:

- `date`
- `color`
- optional `label`

The `color` field should carry exactly one of:

- `empty`
- `low`
- `medium`
- `high`
- a direct hex color string beginning with `#`

If the backing `daily_aggregate.title` is `NULL`, the `label` field should be
omitted from the JSON payload entirely rather than sent as `null`.

### Removed Field Direction

Remove the following fields from the exploration grid response:

- `activity_score`
- `has_data`
- `count`

The grid should no longer expose these values once the server already resolves
the final day color and the optional short label.

An empty day should be represented solely through `color = "empty"`.

### Backend Read Direction

Update the exploration grid provider and schemas so:

- score-based views still resolve `color` from the selected view metadata
- direct-color views return the persisted `daily_aggregate.color_value`
- empty or non-matching days resolve to `color = "empty"`
- `label` is sourced from `daily_aggregate.title` when present

The backend should keep ownership of color resolution semantics.

### UI Transport and Projection Direction

Update the UI transport and projection types to match the slimmer contract.

The UI should:

- consume `date`, `color`, and optional `label`
- detect direct colors by checking whether `color` begins with `#`
- continue to treat the known token values as backend-owned semantic colors
- stop depending on `activityScore`, `hasData`, or `count`

### Rendering Direction

Refactor the day-cell rendering so it can:

- render `empty` with the existing empty-cell treatment
- render token colors through the existing view-color token system
- render direct hex colors as the actual cell background color

The UI should not need a second explicit transport flag to distinguish the two
non-empty color families.

### Test Direction

Update backend and UI tests to cover the new contract and rendering behavior.

At minimum, add or update coverage for:

- token-based day colors
- direct hex day colors
- empty days
- omission of `label` when the aggregate title is `NULL`
- absence of legacy per-day fields in the exploration payload

## Out of Scope

- no redesign of bootstrap or day-context endpoints beyond what is required to
  keep type usage coherent
- no reintroduction of count- or score-based tooltip behavior through a second
  API shape
- no generalized theming system for arbitrary per-view rendering

## Acceptance Criteria

- the exploration day payload is reduced to `date`, `color`, and optional
  `label`
- the API no longer returns `activity_score`, `has_data`, or `count`
- token-based views still render correctly
- direct-color views can render validated hex colors without a `color_mode`
  field
- the UI no longer depends on the removed per-day fields
- tests cover both legacy token colors and direct hex colors

## Notes

The compact transport shape is intentional.

The key tradeoff is to keep the response small while still allowing the UI to
distinguish the two color families through one cheap string check:

- known token values remain semantic colors
- `#...` values are rendered directly
