# R-040-05 - Lightroom Catalog Staged Service and Shared Progress

## Goal

Wire the Lightroom connector into the existing staged-ingest architecture so it
behaves like the other modern connectors in the repo:

- thin connector facade
- dedicated collaborators per concern
- generic staged runner
- shared progress runtime
- thin service composition root

This task should prove that Lightroom ingest can fit the established ingest
shape without inventing a one-off orchestration path.

## Dependencies

- `R-040-02`
- `R-040-04`

## Scope

### Introduce a Thin Lightroom Connector Facade

Create a connector facade analogous to the existing structured connectors.

It should compose explicit collaborators for:

- catalog discovery
- read / fetch
- transformation

Its public methods should remain small and intention-revealing, for example:

- discover catalog descriptors
- load catalog payloads
- build canonical asset candidates

Do not let the facade become a new monolith.

### Adapt Lightroom Intake to the Generic Staged Runner

Introduce Lightroom-specific staged runner adapters analogous to the existing
connector-specific `staged.py` modules.

The staged unit should be:

- one catalog descriptor

The strategy should:

- discover one catalog file
- load its rows and XMP payloads
- transform them into asset candidates
- persist those candidates through a Lightroom persistence scope

### Introduce a Lightroom Progress Adapter

Add a Lightroom-specific adapter over the shared progress engine.

It should use the shared generic progress snapshot and lifecycle while exposing
Lightroom-relevant phase progress such as:

- discovery
- catalog loading
- transformation
- persistence

The implementation should reuse the shared progress runtime already used by the
other connectors. Do not add a Lightroom-only progress framework.

### Keep the Service as a Composition Root

Create a `LightroomCatalogIngestionService` that mirrors the role of the other
connector services:

- read runtime configuration
- create the ingest run through the lifecycle coordinator
- build the Lightroom staged strategy and persistence scope
- delegate the orchestration to the generic staged runner

The service should not contain SQL queries, XML parsing, or repository details.

### Define Runtime Configuration for a Single Catalog File

Extend shared runtime settings with one explicit Lightroom catalog path setting.

Recommended direction:

- `PIXELPAST_LIGHTROOM_CATALOG_PATH`

The service should validate that this setting is present and points to a
supported file when the Lightroom source is invoked.

## Out of Scope

- no CLI registration yet
- no end-to-end coverage yet
- no schema changes

## Acceptance Criteria

- a thin Lightroom connector facade exists with explicit discovery, load, and
  transform responsibilities
- Lightroom ingest uses the generic staged runner rather than a bespoke control
  loop
- a Lightroom-specific progress adapter reuses the shared progress runtime
- the Lightroom ingestion service is a composition root rather than the home of
  parsing or persistence logic
- shared runtime settings include one explicit catalog-file path setting

## Notes

This task is the architectural integration step. After it, the connector
should already feel native to the repo even before CLI wiring is added.
