# R-038-06 - Google Maps Timeline CLI, Progress Reporting, and End-to-End Tests

## Goal

Wire the Google Maps Timeline connector into the existing ingest entrypoints,
shared progress reporting, and end-to-end test suite.

## Dependencies

- `R-038-04`
- `R-038-05`

## Scope

### Add Runtime Settings and Ingest Entry Wiring

The runtime settings and entrypoint wiring should expose the new source through:

- `PIXELPAST_GOOGLE_MAPS_TIMELINE_ROOT`
- `pixelpast ingest google_maps_timeline`
- the shared supported-source listing

### Reuse Shared Progress Infrastructure

The connector should expose progress through the same shared job-run and CLI
reporting path already used by the other ingestion connectors.

At minimum, progress and summary reporting should expose:

- processed export count
- persisted source count
- persisted event count
- inserted
- updated
- unchanged
- failed
- missing_from_source

If unsupported semantic-segment kinds are skipped, the connector may also
surface deterministic warning messages or a skipped-segment count.

### Cover the Full Ingest Path End to End

Add end-to-end tests that cover at least:

- successful import of the checked-in Google Maps Timeline fixture
- transform behavior using an additional synthetic aligned-timestamp payload for
  activity-path clipping
- repeated import of unchanged data
- repeated import after a visit is removed
- repeated import after an activity is removed
- CLI-visible `missing_from_source` reporting
- clear failure for unsupported old-format exports

### Keep Fixture Use Intentional

The checked-in anonymized fixture should remain the structural characterization
anchor, but the end-to-end suite should not rely on it alone.

At least one additional focused synthetic fixture or inline payload should be
used for:

- path clipping into an activity window
- duplicate visit hierarchy normalization
- old-format rejection

## Out of Scope

- no source-specific daily-view registration yet
- no UI work yet

## Acceptance Criteria

- the new connector is available through the shared ingest CLI entrypoint
- runtime settings expose a dedicated root path for the export file
- progress reporting reuses the shared job-run infrastructure
- end-to-end tests cover successful import, repeated unchanged import, removed
  event delete sync, and old-format rejection
- the suite includes at least one aligned-timestamp synthetic payload in
  addition to the checked-in anonymized fixture

## Notes

This task is the point where the research-backed transform rules become part of
the normal developer workflow and regression suite.
