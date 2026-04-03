# R-047 - Person Group Color and Cross-View Filtering

## Goal

Introduce a first explicit visual identity and filtering model for
`PersonGroup` across the `Photo Album` and `Social Graph` views.

This series should make person groups visible and actionable in the product
without inventing a second parallel filter system.

The direction is:

- each `PersonGroup` may carry an optional UI-owned `color_index`
- the UI maps each index to a curated theme-specific palette color
- `PersonGroup` becomes a first-class global filter dimension
- the `Photo Album` view shows relevant groups per folder or collection
- the `Social Graph` view can be filtered by person group and colors nodes by
  their primary matching group

## Dependencies

- `R-035`
- `R-042`
- `R-044`
- `R-045`
- `R-046`

## Scope

This task series covers four connected concerns:

- persisted `PersonGroup` UI metadata for a palette-backed `color_index`
- manage-data API and UI support for editing that color assignment
- shared app-state and API filtering support for global `PersonGroup` filters
- album-view and social-graph rendering that consume group color and filter
  semantics

### Use Color Index, Not Raw Color Values

`PersonGroup` should not store hex values or CSS tokens directly.

Instead, persist a small integer in `PersonGroup.metadata_json`, for example:

```json
{
  "ui": {
    "color_index": 3
  }
}
```

The backend owns only the numeric identifier.
The UI owns the actual palette mapping for the active theme.

This keeps the data model stable while allowing future theme variants such as:

- default pastel
- high contrast
- dark mode

### Treat Person Group As A Global Filter Dimension

The app should gain a shared selected-person-group filter state.

That filter must apply consistently across views instead of being implemented
as one-off local controls:

- `Photo Album`
  - constrains visible folder and collection navigation results
- `Social Graph`
  - constrains the graph projection to matching group members

This series should not introduce a separate album-only or graph-only person
group filter model.

### Make Album Group Relevance Visible But Compact

The album view should expose relevant groups per folder or collection without
turning the navigation tree into a noisy legend wall.

The preferred direction is:

- small colored chips, strips, or badges
- top-ranked groups visible directly
- overflow hidden behind a compact summary affordance such as `+2`

This series should not start with one giant full-color block per album node.

### Keep Social Graph Coloring Deterministic

People may belong to multiple groups.
The social graph still needs one stable node color in v1.

This series should therefore define a deterministic primary-group resolution
rule instead of relying on ambiguous "first found" behavior.

Recommended rule:

- take the first matching group after sorting by `lower(name)` and then `id`
- use only groups that have a configured `color_index`
- fall back to a neutral node style if none exist

## Subtasks

- `R-047-01` - Person group UI metadata and manage-data API foundation
- `R-047-02` - Manage-data person-group color-index editor
- `R-047-03` - Global person-group filter state and shell foundation
- `R-047-04` - Album API person-group relevance and filtering
- `R-047-05` - Album view person-group chips and filter interactions
- `R-047-06` - Social graph person-group coloring and filtering

## Out of Scope

- no free-form hex color editing
- no user-authored theme editor
- no per-view independent person-group filter state
- no weighted multi-color gradients for one social-graph node
- no attempt to infer a canonical "primary group" onto `Person`
- no asset-level person-group scoring model beyond the existing album-aggregate
  derivation

## Acceptance Criteria

- a task series exists for adding `PersonGroup` color identity and global
  filtering
- the series uses persisted `color_index` metadata instead of raw color values
- the series separates manage-data editing, shared filter state, album
  integration, and social-graph integration into focused subtasks
- the series defines deterministic social-graph node coloring for
  multi-group-membership persons
- the series explicitly keeps theme palette ownership in the UI

## Notes

This series should stay disciplined about ownership:

- database stores group UI metadata as a stable integer
- API transports that integer explicitly
- UI decides how each index renders in the active theme
- app state owns the global selected-person-group filter
