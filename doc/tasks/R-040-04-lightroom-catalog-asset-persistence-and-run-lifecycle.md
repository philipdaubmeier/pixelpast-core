# R-040-04 - Lightroom Catalog Asset Persistence and Run Lifecycle

## Goal

Persist Lightroom asset candidates through the existing repository and staged
ingest boundaries without introducing any canonical schema changes.

This task should make the Lightroom connector operational at the persistence
layer while respecting the current model:

- assets upsert by `external_id`
- creator persists through the existing asset creator relation
- keywords persist through `Tag` and `AssetTag`
- named faces persist through `Person` and `AssetPerson`
- Lightroom-specific metadata persists through `Asset.metadata_json`

## Dependencies

- `R-040-03`

## Scope

### Introduce a Lightroom Asset Persister

Create a dedicated Lightroom persistence component analogous to the existing
photo asset persister.

It should own:

- creator person resolution
- asset upsert execution
- tag materialization
- asset-tag replacement
- person materialization
- asset-person replacement
- deterministic persistence outcome calculation

Do not place repository calls inside the connector itself.

### Reuse the Existing Canonical Model Without Migrations

This task must explicitly avoid schema changes.

Required constraints:

- no Alembic migration
- no new canonical tables
- no new asset columns

The Lightroom connector must persist against the existing model exactly as it
exists today.

### Persist Lightroom-Specific Metadata in `Asset.metadata_json`

Everything not represented canonically must be written into the existing asset
JSON field.

That includes:

- file path provenance
- preserved filename
- caption
- camera/lens/exposure metadata
- rating and color label
- collection memberships
- face rectangles

Do not introduce event-like raw payload handling for assets.

### Introduce a Lightroom Run Coordinator

Add a Lightroom-specific lifecycle collaborator responsible for:

- creating or updating the connector source record
- creating the ingest run
- initializing shared progress state

The source should be catalog-scoped in v1.

Recommended direction:

- `Source.type = "lightroom_catalog"`
- `Source.name` is a stable human-readable connector name
- `Source.external_id` is derived from the resolved catalog path
- `Source.config` stores the resolved catalog path

### Define Idempotency Explicitly

The connector must be idempotent without changing the schema.

The first acceptable idempotency model is:

- upsert assets by XMP `DocumentID`
- replace asset-tag links on each run
- replace asset-person links on each run
- update `Asset.metadata_json` when Lightroom metadata changed

This should make repeated imports of the same catalog deterministic even after
file renames inside Lightroom.

### Define Missing-From-Source Semantics Conservatively

Because the current canonical `Asset` model is not source-scoped and the
connector must not add schema, v1 should avoid pretending it can do reliable
source-scoped delete synchronization.

Define the first-version behavior explicitly:

- no asset delete synchronization
- `missing_from_source` remains informational only
- reporting `0` is acceptable if no reliable source-scoped asset comparison can
  be derived from the existing model

Do not invent brittle deletion heuristics just to mimic the photo connector.

## Out of Scope

- no service composition wiring yet
- no CLI registration yet
- no derive-table materialization for collections or face rectangles

## Acceptance Criteria

- Lightroom asset persistence is implemented behind repositories, not inline in
  the connector
- repeated imports are idempotent through `DocumentID`-based asset upserts
- creator, tags, and named faces are persisted through the existing canonical
  relation tables
- Lightroom-specific non-canonical metadata persists through
  `Asset.metadata_json`
- a Lightroom-specific run coordinator exists and uses the shared job-run
  infrastructure
- no migration or canonical schema change is required

## Notes

This task intentionally accepts the limits of the current canonical asset
model. The goal is a clean connector now, not speculative schema work.
