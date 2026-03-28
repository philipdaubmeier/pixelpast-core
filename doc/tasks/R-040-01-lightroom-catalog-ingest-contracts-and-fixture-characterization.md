# R-040-01 - Lightroom Catalog Ingest Contracts and Fixture Characterization

## Goal

Define the public contracts and executable baseline for the new Lightroom
Classic catalog connector before discovery, persistence, and CLI wiring are
added.

The first Lightroom increment has more structure than the existing photo-file
connector:

- one configured catalog file
- one SQLite-backed metadata graph
- one chosen image row per physical file
- one canonical asset candidate per chosen image
- additional fan-out data for tags, persons, collections, and face regions

That structure should be made explicit in contracts and fixture-backed tests
before implementation details spread across ad-hoc helpers.

## Dependencies

- `R-022-08`

## Scope

### Introduce Lightroom-Specific Contracts

Define the small set of connector contracts needed by later tasks, for example:

- one discovered catalog descriptor
- one chosen Lightroom image row projection
- one decompressed XMP payload contract
- one canonical Lightroom asset candidate
- one Lightroom transform error
- one final Lightroom ingestion result

These contracts should model the real staged unit of work:

- one catalog file
- many asset candidates

Do not shape them around event ingestion or photo-file exiftool batches.

### Characterize the Repository Fixture

Add tests that read the checked-in fixture catalog directly:

- `test/assets/lightroom-classic-catalog-test-fixture.lrcat`

The tests should pin the first expected behaviors from that real catalog:

- the file is an SQLite database readable without Lightroom
- the connector-relevant tables exist
- `Adobe_images.id_local` is the central image key used by the relevant joins
- `Adobe_AdditionalMetadata.xmp` is present for chosen image rows
- the configured fixture contains at least one row covering:
  - XMP `DocumentID`
  - XMP `PreservedFileName`
  - XMP `dc:title`
  - hierarchical keywords
  - face data

The current checked-in fixture does not contain non-null IPTC captions or
concrete static collection memberships in `AgLibraryCollectionImage`.
Characterization tests should pin that reality explicitly so later tasks do not
assume sample data that is not actually present.

The tests should characterize the fixture through real SQL reads rather than
through hand-built fake row dictionaries only.

### Characterize XMP Decompression Semantics

Add executable tests that make the XMP blob format explicit:

- the SQLite value is a BLOB
- bytes from offset `4` onward are zlib-compressed content
- `zlib.decompress(blob[4:])` yields the uncompressed XMP XML
- the root XML shape is:
  - `x:xmpmeta`
  - `rdf:RDF`
  - `rdf:Description`

The tests should pin the exact extraction rule used by later tasks so it does
not get re-litigated inside transform code.

### Define the Canonical Mapping Boundaries Up Front

Make the first-version storage contract precise before persistence is added.

Required canonical mappings:

- `Asset.external_id` <- XMP `xmpMM:DocumentID`
- `Asset.summary` <- first `dc:title > rdf:Alt > rdf:li`
- `Asset.timestamp` <- `Adobe_images.captureTime`
- `Asset.latitude` / `Asset.longitude` <- EXIF GPS
- creator relation <- Lightroom creator metadata
- `Tag` / `AssetTag` <- hierarchical keywords
- `Person` / `AssetPerson` <- named faces

Required non-canonical mappings:

- all Lightroom-specific fields not represented canonically must be stored in
  the existing asset-side JSON payload field:
  - `Asset.metadata_json`

That includes at minimum:

- current file name
- current file path
- preserved file name
- caption
- camera
- lens
- aperture
- shutter speed
- ISO
- rating
- color label
- collection memberships
- face rectangles

Do not introduce a new `Asset.raw_payload` field or any schema extension in
this task series.

### Define the No-Schema-Change Constraint Explicitly

Pin the implementation constraint in tests and documentation:

- the Lightroom connector must use the existing canonical schema only
- no Alembic migration is allowed for the v1 connector
- no new canonical tables may be added for collections, face rectangles, or
  Lightroom-specific metadata

## Out of Scope

- no SQLite discovery or loader implementation yet
- no transform implementation yet
- no persistence implementation yet
- no CLI or entrypoint wiring yet

## Acceptance Criteria

- Lightroom-specific contract types exist for catalog discovery, transform
  output, and final result reporting
- automated tests read the checked-in `.lrcat` fixture directly
- the XMP blob decompression rule `zlib.decompress(blob[4:])` is pinned in
  executable tests
- the tests explicitly document that the connector uses existing `Asset`
  fields plus `Asset.metadata_json` rather than requiring schema changes
- the contract layer makes one catalog file producing many asset candidates
  explicit

## Notes

This task is intentionally conservative. Its main value is to freeze the input
shape and the no-schema-change storage boundary before implementation details
spread into the connector.
