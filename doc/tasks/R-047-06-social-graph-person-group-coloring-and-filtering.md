# R-047-06 - Social Graph Person-Group Coloring and Filtering

## Goal

Apply the new global person-group filter and person-group color model to the
`Social Graph` projection.

## Dependencies

- `R-035-03`
- `R-035-04`
- `R-035-05`
- `R-047-01`
- `R-047-03`

## Scope

### Add Person-Group Filter Support To The Social-Graph Endpoint

The social-graph API should accept selected `person_group_ids`.

When a person-group filter is active:

- only persons belonging to at least one selected group remain in the graph
- edges are recalculated or filtered to the remaining node set

This should behave as a true graph projection filter, not as a client-only
hide/show trick after loading the full graph.

### Expose Group Color Metadata Needed By The UI

The social-graph response should expose enough group metadata for node-color
resolution.

At minimum, the UI needs:

- each node's matching groups
- those groups' `color_index`

### Color Each Person By One Deterministic Primary Group

In v1, each social-graph node should render with one group color at most.

Use a deterministic rule:

- consider only matching groups with a configured `color_index`
- sort by `lower(group_name)` and then `group_id`
- take the first group from that ordered set
- fall back to a neutral node color when none qualify

This task should not rely on insertion order from `PersonGroupMember`.

### Keep Group Filtering Global

The social graph should react to the same shared top-bar person-group filter
introduced for the album view.

This task should not create a second graph-local person-group picker.

## Out of Scope

- no multi-color segmented nodes
- no per-edge coloring by group
- no force-layout redesign solely for this feature

## Acceptance Criteria

- the social-graph endpoint accepts selected `person_group_ids`
- active person-group filters constrain the projected graph server-side
- the UI colors person nodes using one deterministic group color when possible
- persons without a qualifying colored group fall back to a neutral style
- the social graph consumes the shared global person-group filter instead of a
  local duplicate control

## Notes

The main product value here is interpretability:

- filter the graph down to the social slice you care about
- read group identity immediately from node color

That is enough for v1.
