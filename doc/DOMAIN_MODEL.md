# PixelPast – Domain Model v0.1

## Core Concepts

### Source

Represents a data source.

- id
- name
- type
- config
- created_at

### ImportRun

Tracks execution of ingestion jobs.

- id
- source_id
- started_at
- finished_at
- status
- mode (full | incremental)

### Event (central timeline unit)

- id
- source_id
- type
- timestamp_start
- timestamp_end
- title
- summary
- location_id (nullable)
- raw_payload (JSON)
- derived_payload (JSON)
- created_at

Initial Event Types:
- media
- calendar
- music_play
- financial_transaction
- trip
- work_activity

### Asset (for media like photos, videos, audio, documents)

- id
- event_id
- path
- checksum
- media_type
- captured_at
- metadata (JSON)

### Location

- id
- name
- latitude
- longitude
- metadata (JSON)

### Person

- id
- name
- metadata (JSON)

### DailyAggregate

- date
- total_events
- activity_score
- media_count
- music_count
- finance_count
- trip_count
- metadata (JSON)

## Design Decision

Event is the universal time-based abstraction.
Specialized tables may be introduced later when justified by analytical needs.