# R-041-01 - Shared Staged Ingestion Service Base

## Goal

Extract the repeated staged-ingestion service wiring into one reusable base for
modern ingestion connectors.

The current service modules for photos, calendar, Spotify, Google Maps
Timeline, workdays vacation, and Lightroom all follow the same orchestration
shape:

- resolve and validate a configured root
- create a job run through a lifecycle coordinator
- build a progress adapter
- build a staged persistence scope
- delegate execution to the generic staged runner

This task should remove that boilerplate without changing observable ingest
behavior, result contracts, or connector responsibilities.

## Dependencies

- none

## Scope

### Introduce a Reusable Ingestion Service Base

Create a generic base or equivalent shared composition helper for staged
ingestion services.

It should own the repeated orchestration shell while allowing connector-specific
hooks for:

- runtime-root resolution and validation
- staged strategy construction
- progress tracker construction
- persistence scope construction
- optional result post-processing

Keep connector-specific public service classes in place. The goal is to
collapse repeated wiring, not to remove explicit source-named entrypoints.

### Preserve Connector-Specific Service Differences

The shared base must support the existing minor variations without forcing
awkward conditionals into the base:

- Google Maps Timeline root resolution
- Lightroom start and end index options
- Google Maps Timeline post-run validation behavior
- connector-specific configuration error messages

Prefer template methods or small injected builders over flag-heavy branching.

### Keep Services as Composition Roots

Do not move connector-specific discovery, parsing, or persistence logic into the
new base.

The service layer should remain a thin composition root that wires together:

- connector facade
- lifecycle coordinator
- progress adapter
- staged runner strategy
- persistence scope

## Out of Scope

- no staged-runner protocol changes
- no connector API changes
- no CLI command changes
- no result-schema changes

## Acceptance Criteria

- the repeated staged-ingest service orchestration is centralized in one shared
  base or helper
- each connector keeps its own explicit public service class
- service-level behavior, validation messages, and result contracts remain
  unchanged
- the shared abstraction does not absorb connector-specific domain logic

## Notes

This task targets only the repeated composition shell. The connector-specific
facades and staged strategies should remain explicit and readable.
