# R-040-02 - Lightroom Catalog Discovery and Read Boundary

## Goal

Introduce a dedicated discovery and read layer for Lightroom catalog intake so
the connector stays honest about its actual concerns:

- validate one configured catalog file
- open the SQLite catalog read-only
- load only the selected Lightroom rows needed for the v1 subset
- keep XMP loading separate from canonical transformation

This task should mirror the architectural separation already used by the
existing connectors while respecting that Lightroom intake is a single-document
SQLite source rather than a directory of files.

## Dependencies

- `R-040-01`

## Scope

### Introduce a Dedicated Catalog Discoverer

Create a discovery component responsible for:

- validating the configured Lightroom catalog path
- accepting a single file input only
- rejecting directories and unsupported file types deterministically
- accepting Lightroom catalog extensions that are actually useful in this repo,
  such as:
  - `.lrcat`
  - `.sqlite`
- producing one discovered catalog descriptor with:
  - resolved absolute path
  - original configured path
  - file extension

This component should not open SQLite or parse any rows yet.

### Separate Catalog Discovery from SQLite Loading

Introduce a dedicated read / fetch layer that owns:

- opening the catalog read-only
- issuing the selected SQL queries
- returning typed row projections or loader payloads

Keep the stage boundaries explicit:

- discover one catalog descriptor
- load base rows and XMP blobs
- transform loader payloads into canonical candidates

Do not collapse discovery and transformation into one connector method.

### Read SQLite in a Bounded, Read-Only Way

The loader should be explicit about safe intake:

- open the catalog in read-only mode
- avoid any SQLite writes, journal mutations, or schema inspection side effects
- avoid loading the full catalog into memory when only a selected subset is
  needed

The implementation should make it possible to stream or batch row loading later
if large real catalogs require it.

### Load One Chosen Lightroom Image Row per Physical File

This task should establish the loader-side dedupe boundary:

- group by `Adobe_images.rootFile`
- choose the lowest `Adobe_images.id_local` per `rootFile`
- treat the chosen row as the only v1 representation for that physical file

Do not interpret virtual copies semantically in this task beyond that dedupe
rule.

### Split Base Rows from Fan-Out Reads

The loader should make these read responsibilities explicit:

- base per-asset rows
  - file path data
  - capture timestamp
  - EXIF/IPTC scalar metadata
  - raw XMP blob
- face rows
- collection membership rows

Do not build one giant SQL join that multiplies rows across faces and
collections.

### Keep Keyword Loading Flexible

Because v1 intends to use XMP `lr:hierarchicalSubject` as the primary keyword
source, this task does not need to make `AgLibraryKeywordImage` the default
loading path.

However, the loader should leave room for later validation or fallback reads
from:

- `AgLibraryKeywordImage`
- `AgLibraryKeyword`

if fixture expansion later proves that some catalogs diverge from XMP.

## Out of Scope

- no canonical transformation yet
- no repository writes yet
- no service orchestration yet
- no CLI configuration wiring yet

## Acceptance Criteria

- a dedicated discoverer exists for single-file Lightroom catalog intake
- a dedicated read/fetch layer exists for read-only SQLite loading
- the loader reads only the selected v1 metadata subset instead of materializing
  the whole catalog
- the chosen-image dedupe rule by `rootFile` is explicit at the read boundary
- face rows and collection rows are loaded through separate fan-out reads rather
  than one inflated join

## Notes

This task should leave a connector that knows how to discover and read a
catalog, but still does not know how to turn that data into canonical assets.
