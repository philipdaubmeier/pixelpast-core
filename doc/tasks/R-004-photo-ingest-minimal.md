# R-004 – Minimal Photo Asset Ingestion

## Goal

Implement minimal ingestion for photo assets from a configured directory.

This establishes the first real end-to-end vertical slice.

---

## Scope

Implement:

- Recursive directory scan
- Detect image files:
  - jpg, jpeg, png, heic
- Extract:
  - timestamp (EXIF/IPTC/XMP DatetimeOriginal if available, else read from filename in YYYYMMDD_HHmmss format, if nothing else available take file mtime)
  - latitude / longitude (if available from EXIF/IPTC/XMP)
  - external_id use the canonical absolute file path incl. filename
- Create Asset entries

No Event creation.
No EventAsset linking.

Ensure idempotency:
- Re-running ingestion does not duplicate assets.

Ensure folder synchronization:
- Re-running with changed files (changed timestamps, location, etc.) updates Assets accordingly
- Re-running with removed files in folder or any subfolder will delete Assets accordingly. Search for any Assets with matching folder path prefixes that are orphaned due to the file no longer existing

---

## Out of Scope

- No person detection
- No tag hierarchy import
- No Lightroom metadata import
- No Event generation
- No thumbnail generation

---

## Acceptance Criteria

- Running ingest twice creates no duplicates
- Assets stored with:
  - path
  - checksum
  - captured_at
  - coordinates if available
- Only new files are inserted
- Modified files are updated
- Assets are deleted for removed files in scanned folder
- Proper logging of processed files

---

## Notes

Use incremental mode by default.
Do not prematurely optimize.