# R-047-05 - Album View Person-Group Chips and Filter Interactions

## Goal

Render person-group relevance directly in the `Photo Album` view and let the
user interact with it through the shared global person-group filter model.

## Dependencies

- `R-044-07`
- `R-047-03`
- `R-047-04`

## Scope

### Render Compact Group Indicators On Album Nodes

Folders and collections in the album navigation should display compact
group-relevance indicators.

Preferred direction:

- small colored chips, pills, or strip segments
- show only the top few groups inline
- collapse overflow into a compact `+N` indicator

Each visible group indicator should use the color assigned by `color_index`.

### Show More Than Color Alone

Color should not be the only signal.

The UI should provide at least one additional cue:

- short group label
- tooltip
- popover with counts

The hover or expanded details should expose the aggregate values returned by
the API, such as `8 / 14`.

### Wire Group Interaction To The Shared Filter

Clicking a group indicator should update the shared person-group filter rather
than maintaining a hidden album-local filter state.

Expected direction:

- click adds or toggles the group in the global filter
- album navigation reloads accordingly
- the current active group filter is visually obvious in the album view

### Keep The Navigation Readable

This task should avoid turning the tree into a dense color matrix.

If too many groups are relevant for one node:

- show only the most relevant few inline
- expose the full set on demand

## Out of Scope

- no full legend-management UI
- no drag-and-drop group ordering in the album view
- no new backend logic beyond consuming the API from `R-047-04`

## Acceptance Criteria

- album navigation renders compact, color-backed person-group indicators
- the indicators derive their colors from persisted `color_index`
- the user can inspect more detail than color alone
- interacting with album group indicators updates the shared person-group
  filter
- overflow handling keeps large-group albums readable

## Notes

The album view should communicate "which groups matter here" quickly.
It should not require the user to open a detail pane for every folder just to
understand the social context.
