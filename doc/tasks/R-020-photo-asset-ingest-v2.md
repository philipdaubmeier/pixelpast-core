# R-020 - Photo Asset Ingest v2

## Goal

Evolve the photo ingestion connector from basic asset extraction to robust
metadata-driven enrichment.

This iteration should extend the current photo ingest so that it can read and
persist richer photo metadata across EXIF, IPTC, and XMP areas while remaining
idempotent and resilient against inconsistent real-world files.

The task should build on the current implementation, which already reads
`Date/Time Original` and basic GPS data from EXIF, and push it toward a
production-usable ingest path for photo libraries with richer editorial
metadata.

---

## Scope

Implement the next photo metadata ingestion increment with the following
capabilities.

### Metadata Extraction Coverage

Extend metadata extraction so the connector can read relevant values from:

- EXIF
- IPTC
- XMP

The implementation must be hardened enough to handle cases where:

- a field exists in only one metadata area
- the same logical field exists in multiple metadata areas
- some metadata blocks are missing, malformed, partially populated, or encoded
  inconsistently

At minimum, ingest or resolve the following:

- title / object name
- `Date/Time Original`
- GPS latitude and longitude
- hierarchical tags
- explicit keywords / subject tags
- creator
- face-region persons

The connector should make field resolution explicit and deterministic when
equivalent values can come from multiple metadata sections.

### Tag Ingestion

Add tag ingestion with hierarchy awareness.

The ingest must:

- understand hierarchical tag paths from metadata
- create all tag nodes required by the hierarchy
- normalize and persist the full hierarchy path
- derive the tag display label from the leaf segment only:
  - the last string after the last hierarchy separator
- preserve whitespace, umlauts and special characters in both path and label

Association behavior must be strict:

- create all tags discovered through hierarchical metadata
- link only those tags to the asset that are explicitly present in
  `Keywords` or `Subject`
- do not implicitly attach every intermediate hierarchy node to the asset just
  because it exists in a hierarchical metadata path

### Person Ingestion

Add person ingestion based on face-region metadata.

The ingest must handle:

- multiple persons in the same image
- repeated occurrences of the same person name in one image
- umlauts and special characters in person names

Repeated face-region occurrences of the same person within one asset should be
interpreted correctly but collapsed to one canonical asset-person relation.

For this task, a simple `AssetPerson` relationship is sufficient:

- if the same person appears multiple times in region metadata for one image,
  ingest it as one person linked once to that asset
- duplicate region entries must not create duplicate `Person` or
  `AssetPerson` rows
- the deduplication behavior must be covered by unit tests

### Person Tags and Tag Exclusion

Photo metadata may encode the same person twice:

- once as a face / region person
- once again as a hierarchical keyword / subject tag

The ingest must reconcile these representations.

If a hierarchical tag path clearly represents a person that is also present in
the image metadata, the ingest must:

- use that hierarchical tag path as the person's canonical path
- associate the person with the asset
- exclude that person-specific path from the asset's tag associations

Example:

- region person: `Lisa`
- tags: `friends/Lisa`, `wedding`

Expected canonical result:

- persons: `{name: "Lisa", path: "friends/Lisa"}`
- tags linked to the asset: `wedding`

This behavior should be implemented deterministically and covered by tests.

### Creator Ingestion

Add creator ingestion for photo assets.

The ingest must:

- read creator-style metadata such as `Creator`, `By-line`, or `Artist`
- create the corresponding `Person` record when missing
- link that person to the asset as the creator

The current canonical model does not have a dedicated creator field on `Asset`.
Because an asset has at most one creator in this domain, the preferred
direction is to evaluate a direct foreign-key reference such as
`Asset.creator_person_id` instead of introducing another join table.

### Canonical Model Review

Review which required attributes are already represented canonically and which
need an explicit schema extension.

Current coverage is partially present:

- `Asset.timestamp` already covers `Date/Time Original`
- `Asset.latitude` and `Asset.longitude` already cover GPS coordinates
- `Tag` and `AssetTag` already cover tag entities and asset-tag links
- `Person` and `AssetPerson` already cover basic person entities and links

Current gaps or insufficiencies are:

- no dedicated canonical creator reference on `Asset`
- no explicit canonical person-path field or equivalent place to store the
  hierarchical path resolved for a person
- no field yet on `Asset` for storing title / object name

This task should make these decisions explicit and implement the minimal schema
changes required to support them cleanly.

For title-like metadata, add a canonical field on `Asset`, for example
`summary`, analogous to `Event.summary`, and persist `Title` / `Object Name`
there.

### Ingestion Hardening

Preserve and extend the connector hardening expectations established in earlier
ingestion work.

The ingest must remain:

- idempotent on repeated execution
- tolerant of partial metadata absence
- deterministic in canonical field resolution
- testable independently from the CLI and API

---

## Out of Scope

- no automatic face detection or ML-based face recognition
- no UI work for rendering face boxes or creator metadata
- no event creation
- no `EventAsset` creation
- no geocoding or reverse geocoding
- no delete synchronization for removed files
- no broad metadata import framework for all future media types

---

## Acceptance Criteria

- the photo ingest can extract title, creator, GPS coordinates, tags, and
  face-region persons from supported photo metadata
- `Date/Time Original` continues to be read correctly and remains the preferred
  canonical timestamp source when available
- hierarchical tags are persisted with full normalized paths and leaf-only
  display labels
- all hierarchy tags are created, but only tags explicitly present in
  `Keywords` or `Subject` are linked to the asset
- multiple persons in one image are imported correctly
- repeated occurrences of the same person name in one image do not cause data
  loss or invalid deduplication and result in one canonical `AssetPerson` link
- if a person is represented both as face metadata and as a hierarchical tag,
  the person inherits the hierarchical path and that person-specific tag is not
  linked as an asset tag
- title / object name metadata is persisted on `Asset` in the dedicated
  canonical field introduced by this task
- creator metadata is represented canonically as a single creator relation on
  the asset rather than an unconstrained many-to-many workaround
- umlauts and special characters round-trip correctly for titles, tags, person
  names, and hierarchy paths
- repeated ingestion runs remain idempotent for assets, persons, tags, and the
  new creator / person-path structures
- missing or incomplete metadata blocks do not break ingestion for otherwise
  valid files
- the repository contains automated tests that read the prepared JPEG fixtures:
  - `test/assets/monalisa-1.jpg`
  - `test/assets/monalisa-2.jpg`
  - `test/assets/monalisa-3.jpg`
- the tests use `test/assets/monalisa_exiftool_output.txt` as the reference for
  expected extracted values
- the tests explicitly verify:
  - title / object name extraction
  - creator extraction
  - GPS extraction
  - hierarchical tag creation
  - explicit asset-tag linking from `Keywords` / `Subject`
  - multiple face regions
  - duplicate same-name person occurrences collapsing to one asset-person link
  - person-path extraction from hierarchical person tags
  - exclusion of person-specific hierarchical tags from asset-tag links
  - Unicode handling for values such as `M\\u00FCnchen` and
    `\\u00E4\\u00F6\\u00FC\\u00DF\\u00C4\\u00D6\\u00DC`

---

## Notes

The unit tests for this task should not rely only on mocked metadata payloads.
They should read the prepared JPEG fixtures directly so the connector is tested
against realistic embedded metadata.

Use `test/assets/monalisa_exiftool_output.txt` as the human-readable reference
for the expected metadata content of the three prepared files. The tests should
translate that reference into explicit assertions against canonical persistence
and association behavior.

Where metadata aliases exist for the same logical field, for example
`Title` versus `Object Name` or `Creator` versus `By-line` versus `Artist`,
the implementation should document and test the chosen canonical precedence
rule.

Pillow may no longer be sufficient for the level of EXIF, IPTC, and XMP parsing
required in this task. `exiftool` is widely regarded as the reference standard
for these metadata areas, so libraries such as `PyExifTool` or other suitable
metadata readers may prove more helpful here. This is a hint, not a mandated
implementation choice.
