# R-040 - Lightroom Catalog Photo Ingest v1

## Goal

Introduce a first Lightroom Classic catalog connector that reads a local
catalog SQLite file and imports a deliberately small, high-value metadata subset
into PixelPast.

This connector must not attempt to ingest the full Lightroom catalog surface.
The catalog contains a very large amount of Adobe-internal state, cloud-sync
bookkeeping, develop history, search/index artifacts, and other data that is
not needed for PixelPast's chronology-first product goal.

The connector should instead focus on:

- one canonical asset per physical photo file
- stable file identity and filesystem provenance
- capture time and location
- editorial metadata
- camera metadata
- keywords
- named face regions
- collection memberships

## Dependencies

- `R-020`
- `R-022-08`
- `R-022-09`
- `R-025`
- `R-029`

## Scope

This task series should introduce a new `lightroom_catalog` ingest source with
the following first-version behavior:

- input is one Lightroom catalog `.lrcat` file, which is a sqlite database
- one canonical source should represent one catalog file path
- canonical source identity should be file-scoped
- the connector should import one canonical asset per physical Lightroom file
- virtual copies must be ignored
- the connector must import only the selected metadata subset documented here
- the connector must parse `Adobe_AdditionalMetadata.xmp` blobs in v1
- canonical asset `external_id` should come from XMP `xmpMM:DocumentID`
- the connector must not import Adobe develop settings, edit history, AI scores,
  sync state, book/slideshow layouts, comments, or other broad catalog state

### Requested Metadata Subset

The current target subset is:

- file name
- file path
- title
- caption / description
- author / creator
- capture date and time
- camera
- lens
- aperture
- shutter speed
- ISO
- rating
- color label
- GPS coordinates
- tags / keywords
- face rectangles with names
- collection memberships

## Catalog Characterization

The analyzed catalog version currently contains:

- `Adobe_images`
- `AgLibraryFile`
- `AgHarvestedExifMetadata`
- `AgLibraryIPTC`
- `AgLibraryKeywordImage`
- `AgLibraryFace`
- `AgLibraryCollectionImage`

The central Lightroom image key is `Adobe_images.id_local`.

### Core Table Graph

The practical base graph for the connector is:

```text
Adobe_images
  -> AgLibraryFile                via Adobe_images.rootFile = AgLibraryFile.id_local
  -> AgLibraryFolder              via AgLibraryFile.folder = AgLibraryFolder.id_local
  -> AgLibraryRootFolder          via AgLibraryFolder.rootFolder = AgLibraryRootFolder.id_local
  -> Adobe_AdditionalMetadata     via Adobe_AdditionalMetadata.image = Adobe_images.id_local
  -> AgHarvestedExifMetadata      via AgHarvestedExifMetadata.image = Adobe_images.id_local
  -> AgHarvestedIptcMetadata      via AgHarvestedIptcMetadata.image = Adobe_images.id_local
  -> AgLibraryIPTC                via AgLibraryIPTC.image = Adobe_images.id_local
  -> AgMetadataSearchIndex        via AgMetadataSearchIndex.image = Adobe_images.id_local
  -> AgLibraryKeywordImage        via AgLibraryKeywordImage.image = Adobe_images.id_local
  -> AgLibraryFace                via AgLibraryFace.image = Adobe_images.id_local
  -> AgLibraryCollectionImage     via AgLibraryCollectionImage.image = Adobe_images.id_local
```

The main lookup tables are:

- `AgInternedExifCameraModel`
- `AgInternedExifLens`
- `AgInternedIptcCreator`
- `AgLibraryKeyword`
- `AgLibraryCollection`

## Physical File Identity And Virtual Copy Handling

The connector must import one canonical asset per physical Lightroom file, not
one asset per `Adobe_images` row.

Observed behavior:

- `Adobe_images` can have duplicate `rootFile` references beyond the first row
- rows can have explicit copy-like markers such as `masterImage` or `copyName`
- Lightroom virtual-copy semantics are not clean enough to require a dedicated
  first-version virtual-copy model

The recommended rule is therefore:

- treat `Adobe_images.rootFile` as the physical-file identity inside the catalog
- keep only the first `Adobe_images` row per `rootFile`
- ignore all later rows for that same `rootFile`
- use the lowest `Adobe_images.id_local` as the deterministic winner

Recommended dedupe pattern:

```sql
WITH chosen_images AS (
    SELECT rootFile, MIN(id_local) AS image_id
    FROM Adobe_images
    GROUP BY rootFile
)
SELECT ai.*
FROM chosen_images ci
JOIN Adobe_images ai ON ai.id_local = ci.image_id;
```

The connector should not attempt to interpret `masterImage`, `copyName`, or
`copyReason` beyond this simple dedupe rule in v1.

Physical row selection and canonical external identity are separate concerns:

- use the first `Adobe_images` row per `rootFile` only to choose the physical
  file representation
- derive canonical asset `external_id` from XMP `xmpMM:DocumentID`
- treat `Adobe_images.id_local` as a Lightroom-row identifier, not as the
  long-term cross-import identity

## Recommended Extraction Direction

The connector should not use one massive all-purpose join for everything.

The recommended shape is:

1. Build one deduplicated base image set keyed by the chosen `Adobe_images`
   rows.
2. Join `Adobe_AdditionalMetadata` and parse the compressed XMP XML for fields
   that only exist there.
3. Extract scalar per-image metadata from the remaining normalized tables.
4. Extract fan-out relations separately:
   - face regions
   - collection memberships
5. Reconstruct collection paths from `parent` chains, not from `genealogy`.

This keeps extraction explicit and avoids accidental Cartesian blowups between
XMP-derived fields, faces, and collections.

## Field Mapping And Formats

### File Name

Primary source:

- `AgLibraryFile.baseName`
- `AgLibraryFile.extension`

Recommended extraction:

- build the display file name as `baseName + '.' + extension` when
  `extension` is present
- keep `AgLibraryFile.originalFilename` as optional provenance only

Note:

- the requested `file name` should use the current catalog-visible file name,
  not the original camera file name

### File Path

Primary source:

- `AgLibraryRootFolder.absolutePath`
- `AgLibraryFolder.pathFromRoot`
- file name from `AgLibraryFile`

Recommended extraction:

- join root folder plus folder path plus current file name
- treat path assembly as path joining, not raw string concatenation

### XMP Metadata Envelope

Primary source:

- `Adobe_AdditionalMetadata.xmp`

Observed blob format:

- the SQLite value is a BLOB
- the first four bytes are a small header
- bytes from offset `4` onward are zlib-compressed XMP XML
- first-version parsing can ignore the header semantics and decompress
  `blob[4:]`

Relevant XML structure:

```text
x:xmpmeta
  -> rdf:RDF
    -> rdf:Description
```

Relevant fields inside that XMP payload:

- `xmpMM:DocumentID`
- `xmpMM:PreservedFileName`
- `dc:title`
- `lr:hierarchicalSubject`

Recommended extraction:

- decompress `xmp[4:]`
- parse the resulting XML once per chosen image row
- store `xmpMM:DocumentID` as canonical asset `external_id`
- treat `xmpMM:DocumentID` as the durable cross-import identity because it
  survives Lightroom renames and remains stable in exported metadata
- store `xmpMM:PreservedFileName` in the assets raw metadata payload for later
  duplicate and provenance analysis

### Title

Primary source:

- XMP path `x:xmpmeta > rdf:RDF > rdf:Description > dc:title > rdf:Alt >
  rdf:li`

Important format note:

- `dc:title` is an alternate-language container
- first-version extraction should use the first `rdf:li` value when present
- v1 does not need language negotiation because the current use case assumes one
  language only

Conclusion:

- `Title` should be extracted from XMP, not from normalized SQLite columns
- the multilingual XMP structure explains why Lightroom does not expose one
  simple canonical SQL `title` column
- smart-collection criteria and search-index tables still confirm that Lightroom
  internally understands title as a first-class concept

### Caption / Description

Primary source:

- `AgLibraryIPTC.caption`

Supporting evidence:

- `AgLibraryIPTC.caption` behaves like Lightroom's caption field, not its title
  field
- this corresponds conceptually to XMP `dc:description`

Recommendation:

- treat `AgLibraryIPTC.caption` as the first-version source for Lightroom
  caption / description
- this is the best current candidate for the German Lightroom UI field
  "Bildunterschrift"

### Author / Creator

Primary source:

- `AgHarvestedIptcMetadata.creatorRef`
- `AgInternedIptcCreator.value`

Join:

```text
AgHarvestedIptcMetadata.creatorRef = AgInternedIptcCreator.id_local
```

### Capture Date And Time

Primary source:

- `Adobe_images.captureTime`

Optional provenance:

- `Adobe_images.originalCaptureTime`

Observed format:

- ISO-like text strings
- most rows are second precision
- some rows include fractional seconds
- a few rows include an explicit UTC offset such as `+00:00`

Recommendation:

- use `Adobe_images.captureTime` as the canonical Lightroom capture timestamp
- parse it as flexible ISO text with optional fractional precision and optional
  timezone offset
- keep `originalCaptureTime` only as optional provenance if needed later

### Camera

Primary source:

- `AgHarvestedExifMetadata.cameraModelRef`
- `AgInternedExifCameraModel.value`

### Lens

Primary source:

- `AgHarvestedExifMetadata.lensRef`
- `AgInternedExifLens.value`

### Aperture

Primary source:

- `AgHarvestedExifMetadata.aperture`

Important format note:

- the stored value is an APEX aperture value, not a user-facing f-number

Recommended conversion:

```text
f_number = 2 ^ (aperture_apex / 2)
```

### Shutter Speed

Primary source:

- `AgHarvestedExifMetadata.shutterSpeed`

Important format note:

- the stored value is an APEX shutter-speed value, not seconds

Recommended conversion:

```text
seconds = 2 ^ (-shutter_speed_apex)
```

The connector should convert this into a human-meaningful duration rather than
persisting the raw APEX value.

### ISO

Primary source:

- `AgHarvestedExifMetadata.isoSpeedRating`

### Rating

Primary source:

- `Adobe_images.rating`

Observed values:

- `NULL` for unrated
- `1` to `5` for star ratings

### Color Label

Primary source:

- `Adobe_images.colorLabels`

Important note:

- the stored label text is localized or user-visible text, not a safe canonical
  enum

Recommendation:

- import the raw Lightroom label text as stored
- optionally normalize it later in connector code to a small internal enum if
  the product needs that

### GPS Coordinates

Primary source:

- `AgHarvestedExifMetadata.hasGPS`
- `AgHarvestedExifMetadata.gpsLatitude`
- `AgHarvestedExifMetadata.gpsLongitude`

Observed format:

- decimal latitude and longitude values

Recommendation:

- trust `hasGPS = 1` as the presence flag
- import latitude and longitude directly as decimals

### Tags / Keywords

Primary source:

- XMP path `x:xmpmeta > rdf:RDF > rdf:Description > lr:hierarchicalSubject >
  rdf:Bag > rdf:li`

Observed format:

- one full hierarchical keyword path per `rdf:li`
- the hierarchy delimiter is `|`

Recommendation:

- use `lr:hierarchicalSubject` as the primary first-version source for
  hierarchical keywords
- split each `rdf:li` on `|`
- preserve the full hierarchy path
- derive the leaf display label from the last path segment
- treat `AgLibraryKeywordImage` and `AgLibraryKeyword` as secondary validation
  or fallback sources only if later fixture characterization finds divergence
- do not infer face membership from hierarchical keywords

### Face Rectangles With Names

Primary tables:

- `AgLibraryFace`
- `AgLibraryKeywordFace`
- `AgLibraryKeyword`

Join:

```text
AgLibraryFace.id_local = AgLibraryKeywordFace.face
AgLibraryKeywordFace.tag = AgLibraryKeyword.id_local
```

Coordinates:

- `tl_x`, `tl_y`
- `tr_x`, `tr_y`
- `bl_x`, `bl_y`
- `br_x`, `br_y`

Observed format:

- normalized floating-point coordinates in the range `0..1`
- the values represent a face rectangle as four corners

Recommendation:

- import face rectangles from `AgLibraryFace`
- import names from `AgLibraryKeywordFace -> AgLibraryKeyword.name`
- treat these as a distinct face-region extraction path, not as ordinary
  keyword membership
- ignore `AgLibraryFaceData` in v1
- drop orphan `AgLibraryKeywordFace` rows that do not resolve to a real face
- treat resolved face names as person-like metadata, even though Lightroom
  stores them through keyword rows of `keywordType = "person"`

### Collections

Concrete membership tables:

- `AgLibraryCollectionImage`
- `AgLibraryCollection`

Join:

```text
AgLibraryCollectionImage.collection = AgLibraryCollection.id_local
AgLibraryCollectionImage.image = Adobe_images.id_local
```

Hierarchy:

- `AgLibraryCollection.parent` defines the real collection hierarchy
- `AgLibraryCollection.genealogy` is not a human-readable collection path

Recommendation:

- import concrete collection memberships from `AgLibraryCollectionImage`
- reconstruct human-readable collection paths by following `parent`
- do not rely on `imageCount`, which is often null in this catalog

Important distinction:

- static collections have concrete membership rows
- smart collections are rule definitions stored in `AgLibraryCollectionContent`
  with `owningModule = 'ag.library.smart_collection'`
- smart collections do not have persisted image membership rows in
  `AgLibraryCollectionImage`

Conclusion:

- v1 should import concrete static collection memberships only
- if PixelPast later wants smart collection membership, that must be implemented
  as Lightroom-rule evaluation, not as a simple join
- published collections can remain out of scope until a real catalog requires
  them

## Search Index And Property Tables

The following tables are useful as supporting evidence but should not be used as
primary extraction sources:

- `AgMetadataSearchIndex`
- `Adobe_imageProperties`

### AgMetadataSearchIndex

Observed behavior:

- contains tokenized search terms for title-like metadata and other facets
- does not preserve enough structure to reconstruct exact text values

Conclusion:

- useful as evidence that Lightroom internally indexes `title`
- not suitable as the canonical extraction source for title or caption because
  it is lossy and tokenized

### Adobe_imageProperties

Observed behavior:

- `Adobe_images.propertiesCache` points to `Adobe_imageProperties.id_local`
- sampled `propertiesString` values contain lightweight Adobe property payloads
  such as loupe focus points
- no title, caption, description, or headline values were found there

Conclusion:

- not needed for the requested v1 subset

## Recommended Query Split

The first connector implementation should roughly split extraction into these
queries:

### 1. Base Asset Query

Fetch one deduplicated row per physical file with:

- chosen `Adobe_images` row
- file name and file path
- the raw `Adobe_AdditionalMetadata.xmp` blob
- capture time
- camera metadata
- creator
- rating
- color label
- GPS
- caption

### 2. XMP Parse Step

Parse the decompressed XMP XML for:

- canonical asset `external_id` from `xmpMM:DocumentID`
- raw metadata `PreservedFileName` from `xmpMM:PreservedFileName`
- `Title` from `dc:title > rdf:Alt > rdf:li`
- hierarchical keywords from `lr:hierarchicalSubject > rdf:Bag > rdf:li`

### 3. Face Query

Fetch all face rows for the chosen image rows with:

- image id
- face id
- rectangle coordinates
- region/orientation metadata
- resolved face name

### 4. Collection Query

Fetch all concrete collection memberships for the chosen image rows with:

- image id
- collection id
- collection name
- collection parent

Build the human-readable collection path in application code or a recursive
CTE.

## Out Of Scope

- no attempt to ingest all Lightroom metadata
- no broad XMP import beyond the selected fields
- no import of develop settings or develop history
- no import of Adobe AI/culling/search-vector tables
- no import of smart collection memberships by evaluating smart rules
- no import of face embedding data from `AgLibraryFaceData`
- no cloud-sync or publish-service state import
- no book, slideshow, print, or web module extraction

## Open Questions

- Does the existing canonical asset schema already expose enough fields for:
  - caption
  - creator
  - color label
  - collection memberships
  - face rectangles
- Should `AgLibraryKeywordImage` / `AgLibraryKeyword` remain only a validation
  path, or do later fixture catalogs require them as a fallback source for
  hierarchical keywords?
- Should person-type keyword assignments later map into canonical `Person`
  entities, canonical `Tag` entities, or both?

## Suggested Subtasks

- `R-040-01`
  - define Lightroom contracts and characterize the checked-in fixture catalog
- `R-040-02`
  - implement single-file discovery and the read-only SQLite load boundary
- `R-040-03`
  - implement transformation, XMP parsing, and canonical asset candidate
    mapping
- `R-040-04`
  - implement asset persistence and run lifecycle without schema changes
- `R-040-05`
  - wire the connector into the staged runner and shared progress runtime
- `R-040-06`
  - expose the connector through the CLI and add end-to-end coverage

## Acceptance Criteria

- a task-series document exists for a Lightroom Classic catalog connector
- the document explicitly limits v1 to a curated metadata subset
- the document explicitly requires one imported asset per physical file and the
  ignoring of virtual copies
- the document explicitly requires XMP parsing from `Adobe_AdditionalMetadata`
  and records the `blob[4:]` zlib decompression rule
- the document explicitly requires canonical asset `external_id` to come from
  XMP `xmpMM:DocumentID`
- the document explicitly requires `xmpMM:PreservedFileName` to be preserved in
  the assets raw metadata payload
- the document explicitly records that `AgHarvestedExifMetadata.image` and
  related image joins target `Adobe_images.id_local` in this catalog
- the document explicitly identifies the recommended source tables and XML
  paths for file path, caption, creator, EXIF metadata, GPS, title, keywords,
  faces, and concrete collection memberships
- the document explicitly distinguishes static collections from smart
  collections and rejects smart-membership import in v1
