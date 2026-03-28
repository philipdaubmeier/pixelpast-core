# R-040-03 - Lightroom Catalog Transform and XMP Mapping

## Goal

Turn Lightroom catalog rows and decompressed XMP payloads into canonical asset
candidates without changing the canonical schema.

This is the task where the connector becomes semantically useful:

- `DocumentID` becomes canonical asset identity
- `Title` becomes canonical asset summary
- creator, GPS, tags, and persons are normalized
- Lightroom-only details are packed into the existing asset metadata JSON field

The output of this task should be candidate objects, not committed database
rows.

## Dependencies

- `R-040-01`
- `R-040-02`

## Scope

### Introduce a Dedicated Lightroom Transform Component

Create a focused transform component such as:

- `LightroomCatalogAssetCandidateBuilder`
- `LightroomCatalogTransformer`

It should accept:

- one chosen image base row
- one decompressed XMP payload
- zero or more face rows
- zero or more collection rows

and produce:

- one canonical Lightroom asset candidate

### Extract XMP Fields Deterministically

The transform must parse the decompressed XMP XML and resolve:

- `xmpMM:DocumentID`
- `xmpMM:PreservedFileName`
- first `dc:title > rdf:Alt > rdf:li`
- all `lr:hierarchicalSubject > rdf:Bag > rdf:li`

The extraction rules should be explicit and deterministic:

- `DocumentID` is required for canonical asset identity
- `Title` uses the first available localized `rdf:li`
- hierarchical keywords split on `|`
- empty or whitespace-only values are ignored

### Map Into the Existing Canonical Asset Model Only

The transform must not require schema changes.

Canonical fields:

- `external_id` <- XMP `DocumentID`
- `media_type` <- resolved from the Lightroom file extension and current
  photo-ingest conventions
- `timestamp` <- parsed `Adobe_images.captureTime`
- `summary` <- XMP title
- `latitude` / `longitude` <- EXIF GPS
- creator relation candidate <- IPTC creator
- `tag_paths` / `asset_tag_paths` <- hierarchical keyword paths
- `persons` <- named face persons

Non-canonical Lightroom fields must be packed into the existing
`metadata_json` payload on the asset candidate.

### Define the First-Version `metadata_json` Shape

The transform should produce a stable and documented asset-side metadata shape
using the existing `Asset.metadata_json` field.

At minimum, include:

- `file_name`
- `file_path`
- `preserved_file_name`
- `caption`
- `camera`
- `lens`
- `aperture_f_number`
- `shutter_speed_seconds`
- `iso`
- `rating`
- `color_label`
- `collections`
- `face_regions`

Recommended shape guidance:

- keep top-level keys explicit
- use JSON-native scalars and arrays only
- keep collection entries lightweight:
  - id when useful for traceability
  - name
  - reconstructed path
- keep face region entries lightweight:
  - resolved person name
  - rectangle corners normalized to `0..1`

### Convert Lightroom Numeric Formats

The transform must normalize Lightroom numeric storage formats:

- aperture APEX -> user-facing f-number
- shutter-speed APEX -> seconds
- ISO -> scalar integer-like value when representable

Do not persist raw APEX values as the primary first-version meaning.

### Use XMP Hierarchical Keywords as the Primary Tag Source

For v1, keyword extraction should prefer XMP hierarchical subjects over the
relational Lightroom keyword tables.

The transform must:

- split each hierarchical keyword path on `|`
- normalize it into PixelPast-style path form
- derive the leaf label from the last segment
- produce deterministic tag paths

If later tasks need `AgLibraryKeywordImage` as validation or fallback, that
should stay an implementation detail outside the main transform contract.

### Use Named Faces as Person Candidates

The transform should resolve persons from the Lightroom face tables:

- person name from `AgLibraryKeywordFace -> AgLibraryKeyword.name`
- one canonical person candidate per distinct face name per asset
- face rectangles preserved in `metadata_json`

This keeps person identity canonical while retaining geometric face information
for later derived layers.

## Out of Scope

- no repository writes yet
- no run lifecycle or source persistence yet
- no CLI wiring yet

## Acceptance Criteria

- one loaded Lightroom image payload transforms into one canonical asset
  candidate
- asset `external_id` is derived from XMP `DocumentID`
- asset `summary` is derived from XMP title
- hierarchical keywords come primarily from XMP
- named faces become person candidates while face rectangles remain in
  `metadata_json`
- Lightroom-only fields are stored in the existing asset metadata payload
  rather than requiring schema changes
- aperture and shutter speed are converted from Lightroom storage units into
  user-meaningful values

## Notes

This task should keep transformation pure. The result should be easy to test
from fixture-derived loader payloads without opening a database transaction.
