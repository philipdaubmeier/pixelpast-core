# R-047-04 - Album API Person-Group Relevance and Filtering

## Goal

Extend the album read API so folder and collection navigation can expose
person-group relevance and honor the new global person-group filter.

## Dependencies

- `R-044-04`
- `R-044-05`
- `R-045`
- `R-046`
- `R-047-01`
- `R-047-03`

## Scope

### Expose Relevant Person Groups On Album Nodes

Album navigation and context contracts should surface the relevant
`PersonGroup` rows already materialized by `album-aggregate`.

Returned group entries should include:

- `group_id`
- `group_name`
- `color_index`
- `matched_person_count`
- `group_person_count`
- `matched_asset_count`
- `matched_creator_person_count`

The API should sort groups by strongest relevance first.

Recommended ordering:

- `matched_person_count` descending
- `matched_asset_count` descending
- `lower(group_name)` ascending
- `group_id` ascending

### Honor Global Person-Group Filter In Album Reads

Album endpoints that load folder or collection navigation should accept
selected `person_group_ids` and exclude nodes that are not relevant to any of
those groups.

This should apply to:

- folder tree loading
- collection tree loading
- album context where node summaries are displayed

### Keep Asset Listing Semantics Stable In v1

This task should not invent a separate asset-level person-group filtering model
unless the existing album APIs already require it.

The v1 direction is:

- filter album navigation nodes by group relevance
- keep the selected node's asset listing driven by the selected album node plus
  existing filters

### Reuse Existing Aggregate Rows

The API should consume the existing `album-aggregate` output instead of
recomputing person-group relevance ad hoc per request.

## Out of Scope

- no album UI rendering yet
- no new derive job
- no per-asset person-group explanation payload in this task

## Acceptance Criteria

- album API responses expose relevant person groups with `color_index` and
  aggregate counts
- album navigation endpoints accept selected `person_group_ids`
- folders and collections unrelated to the active group filter are excluded
- album reads reuse persisted `album-aggregate` relevance rows rather than
  recomputing them at request time

## Notes

This task should keep the server contract honest:
album group relevance is derived data and should be served as such, not
re-derived inside route handlers.
