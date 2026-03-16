# R-033-02 - Daily View Score Threshold Color Mapping

## Goal

Extend `daily_view.metadata` so each daily view can define its own mapping from
`activity_score` thresholds to grid `color_value` outputs.

Today the backend hard-codes score-to-color behavior in application logic. That
prevents view-specific color semantics from being defined in the derived data
model itself.

This task should move the score-threshold mapping into `daily_view.metadata` so
the view definition owns how its activity score is translated into grid color
levels.

## Dependencies

- `R-033-01`

## Scope

This task is about the metadata structure and backend consumption of
score-threshold color mappings stored on `daily_view`.

### Required Metadata Direction

Extend `daily_view.metadata` with a structured mapping that defines score
thresholds and their corresponding `color_value`.

The intended shape is a list of threshold entries such as:

```json
[
  { "activity_score": 1, "color_value": "low" },
  { "activity_score": 35, "color_value": "medium" },
  { "activity_score": 70, "color_value": "high" }
]
```

Each entry means:

- if the actual `activity_score` is greater than or equal to the configured
  threshold, that color is eligible
- the selected color is the one from the highest threshold that is still less
  than or equal to the score

If the actual score is below the smallest configured threshold, the resulting
color must default to `empty`.

### Required Backend Direction

Update the backend grid-color resolution so it can read and apply the threshold
mapping from the selected `daily_view.metadata`.

The implementation should evaluate the mapping deterministically:

- sort or otherwise normalize thresholds into stable ascending score order
- choose the highest matching threshold for the given score
- return `empty` if no threshold matches

The mapping should be treated as server-owned derived configuration, not as a
UI concern.

### Validation Direction

Define and enforce the expected metadata constraints for this mapping.

At minimum, the backend should ensure the threshold entries are coherent:

- `activity_score` is an integer threshold
- `color_value` is one of the supported grid color tokens
- invalid or malformed mappings are rejected or handled through an explicit,
  documented fallback path

If a fallback is necessary, it should be narrow and deterministic rather than
silently accepting arbitrary malformed payloads.

### Derive Direction

The derive path that creates or updates `daily_view` metadata should populate
this threshold mapping for the relevant views.

For the initial implementation, it is acceptable to persist the current shared
defaults as view metadata, for example:

```json
[
  { "activity_score": 1, "color_value": "low" },
  { "activity_score": 35, "color_value": "medium" },
  { "activity_score": 70, "color_value": "high" }
]
```

That keeps the current overall semantics while moving the source of truth into
the derived view definition.

## Out of Scope

- no user-facing CRUD for editing view thresholds
- no redesign of non-score-based heuristics beyond what is needed to consume
  threshold mappings
- no frontend-owned color-threshold logic
- no expansion of the grid color vocabulary beyond the existing tokens unless
  separately justified

## Acceptance Criteria

- `daily_view.metadata` can store a score-threshold-to-color mapping
- the backend can read that mapping for the selected view and resolve
  `activity_score` to `color_value`
- a score below the smallest configured threshold resolves to `empty`
- the derive path populates the mapping for persisted daily views
- tests cover threshold ordering, highest-match selection, and the default
  `empty` behavior below the first threshold

## Notes

This task moves color-threshold semantics toward the derived data model without
yet requiring full dynamic user-defined view formulas.

The key correction is:

- the backend should not hard-code score thresholds as universal constants
- each `daily_view` should be able to define its own score-to-color mapping in
  metadata
