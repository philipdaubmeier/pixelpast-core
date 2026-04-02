# R-046 - Person Group Album Aggregate Rules v1

## Goal

Extend canonical `PersonGroup.metadata` so album-level group relevance can be
controlled explicitly without changing the underlying group membership model.

The first concrete need is to support group-specific ignore rules for the
`album-aggregate` derive job.

This should solve the overlap problem where one or two socially central people
cause unrelated albums to match too many groups, for example:

- the same person appearing in both `friends` and `neighborhood`
- spouses or household members appearing in many albums that are not actually
  representative of a broader group context

## Dependencies

- `R-042-04`
- `R-042-05`
- `R-045`

## Scope

### Keep Canonical Group Membership Untouched

This task must not redefine what a person group is.

Required direction:

- `PersonGroupMember` remains the authoritative group membership set
- ignored-person rules affect album relevance derivation only
- the same person may still be a valid canonical member of the group

This distinction is important because the problem is not incorrect membership.
The problem is over-broad album relevance inference.

### Define A Namespaced Metadata Contract

Use `PersonGroup.metadata_json` as the extension point for derive-specific album
rules.

The first-version contract should be:

```json
{
  "album_aggregate": {
    "ignored_person_ids": [1, 2]
  }
}
```

Rules:

- `album_aggregate` is optional
- `ignored_person_ids` is optional
- `ignored_person_ids` must contain canonical `Person.id` values only
- the stored list should be normalized to unique ascending integers

This task should reserve the `album_aggregate` metadata namespace for future
derive-specific rules without implementing them yet.

### Apply Ignore Rules Inside The Album Aggregate Derive Job

Update the `album-aggregate` derive logic so person-group relevance matching
uses:

- canonical group member ids
- minus that group's `album_aggregate.ignored_person_ids`

Semantics:

- ignored persons still belong to the group canonically
- ignored persons do not contribute to `matched_person_count`
- ignored persons do not contribute to `matched_asset_count`
- ignored creator persons do not contribute to
  `matched_creator_person_count`

If all members of a group are ignored for album aggregation, that group should
produce no album relevance rows.

### Validate Metadata Through Manage-Data Boundaries

The manage-data backend should expose and validate this metadata shape
explicitly rather than passing arbitrary JSON through unchecked.

Required outcomes:

- read contracts expose album-aggregate group rules in a typed shape
- save contracts accept album-aggregate group rules in a typed shape
- validation rejects unknown person ids in `ignored_person_ids`
- validation normalizes duplicate ids away

This task should keep the typed API contract narrow. Do not open the whole
`metadata_json` blob for arbitrary client editing.

### Add Manage-UI Editing Support

Extend the person-group editing workflow in the Manage overlay so one group's
album-aggregate ignore list can be maintained in the UI.

Recommended UX direction:

- edit the ignore list from the person-group editor
- use persisted-person search or picker behavior similar to the membership
  editor
- show the ignored persons as an explicit removable list
- clearly label the behavior as album-aggregate-specific

The UI should make it obvious that ignored persons are still group members and
that the setting only affects album inference.

### Keep The Contract Future-Proof But Narrow

This task should intentionally stop at ignored persons.

Do not implement additional album relevance rule types yet such as:

- minimum matched-person thresholds
- minimum coverage ratios
- representative or anchor persons
- weighted scoring

The metadata namespace should make those future additions possible, but this
task should not speculate beyond the one real need already identified.

### Add Tests Across Persistence, Derive, And UI/API Boundaries

Tests should explicitly cover:

- group metadata round-trip through manage-data reads and writes
- validation failure when ignored person ids do not exist
- deduplication and ordering normalization of ignored ids
- album-aggregate derive excluding ignored persons from relevance rows
- groups with all members ignored producing no relevance rows
- UI draft editing and save behavior for ignored persons

## Out of Scope

- no generic metadata editor for arbitrary person-group JSON
- no changes to canonical `PersonGroupMember` semantics
- no threshold-based relevance tuning in this task
- no CLI flags for ad hoc ignored-person overrides

## Acceptance Criteria

- `PersonGroup.metadata_json` has a documented `album_aggregate` rule namespace
- manage-data contracts expose a typed album-aggregate ignored-person rule
- manage-data saves validate ignored person ids against persisted canonical
  persons
- the `album-aggregate` derive job excludes ignored persons on a per-group
  basis
- groups with fully ignored album-aggregate membership do not emit relevance
  rows
- the Manage UI allows editing ignored persons for one person group
- the resulting behavior is explicit, group-specific, and does not alter the
  canonical membership model

## Notes

This task intentionally chooses explicit per-group signal suppression over
global thresholds.

That is the better first solution for overlapping real-world social graphs
because it addresses the actual source of false positives:

- some people are weak signals for one group
- while still being strong signals for another

If later experience shows that ignored-person rules are not sufficient, future
tasks can add more album-aggregate rule types inside the same metadata
namespace.
