# PixelPast – Domain Model v0.1

## Core Concepts

### Source

Represents a data source.

- id
- name
- type
- config (JSON)
- created_at

### ImportRun

Tracks execution of ingestion jobs.

- id
- source_id
- started_at
- finished_at
- status
- mode (`full` | `incremental`)

### Event (central timeline unit)

Represents a meaningful time-based occurrence in the life timeline, such as a calendar entry, trip, financial transaction or music play. Types enumeration can be extended when needed for new connectors.

- id
- source_id
- type (`calendar` | `music_play` | `financial_transaction`)
- timestamp_start
- timestamp_end
- title
- summary
- latitude (nullable)
- longitude (nullable)
- raw_payload (JSON)
- derived_payload (JSON)
- created_at

### Asset

Represents a stored digital object, such as a photo, video, audio file or document. They are located in time by their capture or creation timestamp. Connectors use `external_id` as unique markers to recognize previously added objects, this can be UUIDs, URIs or simply file paths.

- id
- external_id
- media_type (`photo` | `video` | `audio` | `document`)
- timestamp
- latitude (nullable)
- longitude (nullable)
- metadata (JSON) (nullable)

### EventAsset

Optional association between a semantic event and a stored asset.

- event_id
- asset_id
- link_type (`imported` | `derived`)

## Tag

Generic semantic annotation that can be attached to events and assets. Can be hierarchically nested with path if needed and is stored in normalized form, e.g. "activity/wedding/speech" or "travel/italy/venice".

- id
- label
- path (nullable)
- metadata (JSON) (nullable)

## EventTag

Associates events with tags.

- event_id
- tag_id

## AssetTag

Associates assets with tags.

- asset_id
- tag_id

## Person

Represents a known or inferred person.

- id
- name
- aliases (nullable)
- metadata (JSON) (nullable)

## EventPerson

Associates people with events.

- event_id
- person_id

## AssetPerson

Associates people with assets.

- asset_id
- person_id

## PersonGroup

Represents a named group of people. Can be hierarchically nested with path if needed and is stored in normalized form, e.g. "colleagues/mycompany/mydepartment".

- id
- name
- type
- path (nullable)
- metadata (JSON)

## PersonGroupMember

- group_id
- person_id

### DailyAggregate

Derived day-level read model for grid rendering and day summaries.

- date
- aggregate_scope (`overall` | `source_type`)
- source_type
- total_events
- media_count
- activity_score
- tag_summary (JSON)
- person_summary (JSON)
- location_summary (JSON)
- metadata (JSON)

Design note:
- the day grid should read from `DailyAggregate`, not directly from canonical
  `Event` or `Asset` rows
- persistent filtering should increasingly target derived and database-backed
  read models on the server
- canonical associations remain valid sources for reusable catalogs and detail
  reads where explicitly intended

## Design Decision

PixelPast is fundamentally centered around chronology. Every primary entity in the system must be precisely placed in time. Both `Event` and `Asset` are first-class temporal entities and therefore require an explicit timestamp (point in time or time span).

An `Event` represents a meaningful time-based occurrence in the life timeline, such as a calendar entry, trip, financial transaction or music play.

An `Asset` represents a stored digital object, such as a photo, video, audio file or document. Assets have their own capture or creation timestamp and may also include geographic coordinates, but they are not modeled as events by default.

`EventAsset` provides an optional link between both concepts without forcing identity or ownership. This allows the system to associate assets with events when such a relationship is explicitly imported or analytically derived, while keeping both entities independent in the core model.

This design keeps ingestion simple, avoids premature semantic coupling, and leaves room for richer correlations and derived relationships in later layers.
