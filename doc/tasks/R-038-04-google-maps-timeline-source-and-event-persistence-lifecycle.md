# R-038-04 - Google Maps Timeline Source and Event Persistence Lifecycle

## Goal

Persist one Google Maps Timeline export document as one canonical source plus
its canonical visit and activity event set.

The persistence path should follow the same repository and staged-ingestion
boundaries already used by the existing event-based connectors.

## Dependencies

- `R-038-03`

## Scope

### Reuse One Canonical Source Per Export File

The connector should persist one canonical `Source` of type
`google_maps_timeline` for the resolved export file.

Because the export JSON does not expose a stable intrinsic source identifier,
the connector should derive `Source.external_id` from the resolved file path.

The source config should store only lightweight provenance, for example:

- `origin_path`
- `export_format`

### Persist Canonical Events Through Repository Boundaries

The connector should persist its canonical visit and activity events through the
existing source and event repositories rather than writing SQL directly inside
the connector or transform code.

The persistence seam should:

- upsert the source by `Source.external_id`
- replace that source's canonical event set with the transformed candidates
- return detailed outcome counts suitable for shared progress reporting

### Define Stable Event Identity Explicitly

Each emitted event candidate should carry a deterministic `external_event_id`
so repeated imports can classify rows as inserted, updated, unchanged, or
missing.

The identity should be stable across re-import of semantically unchanged
segments and should not depend on mutable path payload details alone.

Practical examples:

- visit identity derived from segment kind, normalized start/end, and resolved
  hierarchy choice
- activity identity derived from segment kind and normalized start/end

### Preserve Only Selected Raw Payload Fields

Persisted event rows should write the transformed selective payload rather than
the entire original JSON segment.

This keeps canonical payloads smaller, more deterministic under tests, and less
coupled to unrelated future Google export fields.

## Out of Scope

- no delete-sync counting yet
- no CLI wiring yet
- no source-specific derived view work

## Acceptance Criteria

- one Google Maps Timeline export file persists as one canonical source of type
  `google_maps_timeline`
- the source is reused across repeated imports of the same file path
- transformed visit and activity candidates persist only through repository
  boundaries
- event persistence outcomes expose inserted, updated, unchanged, and persisted
  counts for shared reporting
- event candidates carry deterministic identities suitable for later delete sync

## Notes

This task should not invent new schema columns. The current canonical event
table is sufficient for v1 if route detail stays inside `raw_payload`.
