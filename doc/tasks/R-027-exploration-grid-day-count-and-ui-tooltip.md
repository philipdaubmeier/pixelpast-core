# R-027 - Exploration Grid Day Count and UI Tooltip

## Goal

Extend the exploration grid API so each returned day includes a count equal to
the sum of `total_events` and `media_count` from the daily aggregate row.

Update the UI so the day-grid tooltip shows that real per-day count instead of
the current placeholder `0` values.

## Dependencies

- `R-024-01`
- `R-024-02`
- `R-023-03`

## Reasoning

The current exploration grid contract is intentionally minimal, but the UI still
needs one concrete numeric value for simple day-cell feedback.

Today the React mapping keeps legacy `eventCount` and `assetCount` fields in the
render projection, but because the backend no longer returns those values they
are hard-coded to zero. That produces misleading tooltip content in the day
grid.

This task adds one explicit derived count to the exploration response without
reintroducing the heavy older per-day payload shape.

## Scope

### Extend the Exploration Grid Day Contract

Add a new per-day numeric field to the exploration endpoint response. The field
should represent:

- `total_events + media_count`

for the matching `DailyAggregate` row of that day.

The field should be present for every returned day in the dense range. For empty
days without a derived aggregate row, the value should be `0`.

The contract should remain otherwise minimal and should not reintroduce:

- separate `event_count`
- separate `asset_count`
- per-day person lists
- per-day tag lists
- any other legacy client-filtering payload

### Source the Count Strictly from Derived Daily Aggregates

The count must be computed from the same derived aggregate row already used for
`activity_score` and `has_data`.

This task should not introduce canonical fallback logic and should not infer the
count by querying events and assets directly.

The intended formula is:

- `count = total_events + media_count`

using the overall daily aggregate row selected for the exploration grid.

### Update Exploration API Mapping and Tests

Adjust the API schemas, providers, and integration tests so the new field is
returned consistently for:

- empty days
- populated days
- filtered days that are suppressed to empty grid cells

If a day is filtered out by persistent server-side filters, its returned count
should follow the same visible-grid semantics as the rest of the day payload.
That means the task must define and test whether filtered-out days surface `0`
or preserve the underlying derived count. The preferred behavior for grid
consistency is to return `0` for filtered-out days together with `has_data =
false`.

### Update the UI Tooltip Projection

Refactor the UI transport and projection mapping so the exploration grid count
is carried through to the day-cell render model.

The day-grid tooltip should display the new count instead of relying on the
legacy placeholder fields that are currently initialized to zero.

The implementation should avoid reintroducing fake split counts in the client.
If the UI needs one display number, it should consume the backend-provided total
count directly.

### Clean Up Legacy Placeholder Logic

Remove or simplify UI code that exists only because the exploration endpoint no
longer returned a count.

This includes reviewing:

- API transport types
- timeline projection mapping
- tooltip rendering logic
- any comments describing the zero-value placeholder workaround

## Out of Scope

- no redesign of the day-grid visual language
- no addition of separate event and asset counts to the grid contract
- no change to hover-context loading
- no change to day-detail endpoint payloads

## Acceptance Criteria

- `GET /exploration` returns a per-day count derived from
  `total_events + media_count`
- empty dense-grid days return `0`
- filtered-out days follow explicit and tested empty-grid semantics
- the UI tooltip displays the real derived count rather than placeholder zeroes
- legacy client-side placeholder mapping for the tooltip is removed or
  simplified
- API and UI tests cover the new field and tooltip behavior

## Notes

This task should preserve the architectural direction established by the split
exploration contract. The grid endpoint may grow by one practical display field,
but it should remain a lightweight derived projection rather than drifting back
toward the older broader heatmap payload.
