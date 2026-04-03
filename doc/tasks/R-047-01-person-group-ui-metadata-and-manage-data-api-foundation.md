# R-047-01 - Person Group UI Metadata and Manage-Data API Foundation

## Goal

Extend the canonical `PersonGroup` manage-data contracts with explicit
UI-oriented metadata for `color_index`.

## Dependencies

- `R-042-02`
- `R-046`

## Scope

### Add Typed Person-Group UI Metadata Contract

The manage-data API should stop treating `PersonGroup.metadata_json` as an
opaque implementation detail for this workflow.

Add explicit transport support for:

- `person_group.ui.color_index`

Contract direction:

- `color_index` is optional
- when present, it must be a positive integer
- the API returns a normalized integer or `null`

### Persist Color Index In `metadata_json.ui`

Server-side persistence should read and write:

```json
{
  "ui": {
    "color_index": 2
  }
}
```

This task should preserve unrelated metadata namespaces such as
`album_aggregate`.

### Keep Validation Tight And Boring

This task should validate shape, not theme policy.

The backend should ensure:

- `color_index` is an integer
- `color_index > 0`

The backend should not hardcode a maximum palette size.
That remains a UI concern because themes may expose different palette lengths
later.

### Extend Read Contracts Needed By Other Views

Any existing API contracts that already expose `PersonGroup` catalog rows for
the client should include the normalized `color_index` field where relevant.

This task is the transport foundation for later:

- manage-data editing
- global person-group filter UI
- album chips
- social-graph node coloring

## Out of Scope

- no manage-data UI control yet
- no global filter state yet
- no album or social-graph rendering changes yet

## Acceptance Criteria

- manage-data read and write contracts support `PersonGroup.ui.color_index`
- persistence stores that value under `metadata_json.ui.color_index`
- unrelated metadata namespaces remain intact when saving
- invalid `color_index` values are rejected server-side
- normalized API responses expose either a positive integer or `null`

## Notes

This task should establish one stable contract shape for UI-owned group
appearance metadata before multiple views start consuming it.
