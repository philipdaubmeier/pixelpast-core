# R-005 - Photo Asset Ingest v1

## Goal

Implement the first real ingestion connector for photo assets from a configured
directory.

This task creates the first end-to-end vertical slice from filesystem discovery
to canonical persistence.

---

## Scope

Implement a photo ingestion flow that:

- scans a configured directory recursively
- detects supported image formats:
  - `jpg`
  - `jpeg`
  - `png`
  - `heic`
- extracts asset timestamp from:
  - EXIF when available
  - otherwise a supported filename pattern such as `YYYYMMDD_HHmmss`
  - otherwise file modification time as a fallback
- extracts latitude and longitude when available
- persists canonical `Asset` records
- records an `ImportRun`
- supports idempotent re-execution

Use the existing canonical model consistently:

- store the stable source-specific identifier in `Asset.external_id`
- store source-specific file details such as absolute path in metadata if needed
- store the temporal value in `Asset.timestamp`

---

## Out of Scope

- No `Event` creation
- No `EventAsset` creation
- No delete synchronization for removed files
- No checksum-based change detection
- No person detection
- No Lightroom import
- No thumbnail generation

---

## Acceptance Criteria

- running ingestion twice does not create duplicate assets
- assets are persisted with timestamp and coordinates when available
- empty directories are handled cleanly
- repeated execution and partial failure behavior are covered by tests
- connector logic remains independently testable

---

## Notes

Keep this task intentionally narrow.
Deletion sync and deeper file-change reconciliation should be handled in a later
hardening task once the basic ingest path is stable.
