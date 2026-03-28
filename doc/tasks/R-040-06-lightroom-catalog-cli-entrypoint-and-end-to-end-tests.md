# R-040-06 - Lightroom Catalog CLI Entrypoint and End-to-End Tests

## Goal

Expose the Lightroom catalog connector through the existing ingest entrypoints
and cover the full workflow with end-to-end tests using the checked-in
fixture catalog.

After this task, `pixelpast ingest lightroom_catalog` should behave like the
other supported ingest sources:

- configured through shared settings
- launched through the shared ingest entrypoint
- progress reported through the shared CLI progress path
- validated through repository-level end-to-end tests

## Dependencies

- `R-040-05`

## Scope

### Register Lightroom Catalog in Shared Ingest Entrypoints

Extend the ingest entrypoint path so:

- `list_supported_ingest_sources()` includes `lightroom_catalog`
- `run_ingest_source(source=\"lightroom_catalog\", ...)` runs the new service
- CLI help and validation expose the new source as supported

Reuse the existing entrypoint pattern. Do not add a Lightroom-only side path.

### Reuse Shared CLI Progress Reporting

The CLI output for Lightroom ingest must reuse the shared progress reporting
already in place.

Required behavior:

- phase transitions are visible through the generic progress contract
- progress updates come from the shared progress runtime
- no Lightroom-specific terminal renderer is introduced

### Add End-to-End Coverage with the Checked-In Fixture

Add end-to-end tests that use:

- `test/assets/lightroom-classic-catalog-test-fixture.lrcat`

The tests should verify persisted canonical outcomes, not only service return
values.

At minimum, cover:

- successful ingest from the fixture catalog
- repeated execution idempotency
- asset reuse by XMP `DocumentID`
- title mapping to `Asset.summary`
- caption mapping into `Asset.metadata_json`
- preserved filename mapping into `Asset.metadata_json`
- keyword persistence into canonical tags
- named face persistence into canonical persons
- collection membership persistence into `Asset.metadata_json`
- face rectangle persistence into `Asset.metadata_json`
- virtual-copy ignoring by `rootFile` dedupe
- progress callback emission through the shared progress path

### Add Negative and Boundary Tests

Add focused tests for important failure modes:

- missing `PIXELPAST_LIGHTROOM_CATALOG_PATH`
- unsupported configured file type
- invalid or unreadable SQLite file
- malformed or undecompressible XMP blob for one image

The connector should fail or degrade deterministically according to the
contracts established in the earlier subtasks.

### Confirm the No-Schema-Change Outcome

The end-to-end tests should prove the connector works without any canonical
schema changes.

Practical checks should include:

- no new migrations are required
- persisted Lightroom data fits into the existing `Asset`, `Tag`, `Person`,
  `AssetTag`, and `AssetPerson` structures
- extra Lightroom metadata is carried through `Asset.metadata_json`

## Out of Scope

- no UI work
- no derived collection or face-region tables
- no additional canonical schema work

## Acceptance Criteria

- `lightroom_catalog` is available through the existing ingest CLI and
  entrypoint path
- the shared CLI progress reporter works for Lightroom ingest without a special
  implementation
- end-to-end tests use the checked-in fixture catalog directly
- repeated runs are idempotent through `DocumentID`-based asset reuse
- the tests confirm that Lightroom-specific extra fields persist through
  `Asset.metadata_json` instead of requiring schema changes
- the full connector operates through the same architectural seams as the
  existing modern connectors in the repo

## Notes

This task should finish the connector as an operational ingest source without
broadening scope into new derived tables or schema redesign.
