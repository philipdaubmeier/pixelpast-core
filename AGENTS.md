# AGENTS.md

This file provides working instructions for coding agents contributing to PixelPast.
It condenses the current project documentation into one implementation-oriented guide.

## Project Identity

PixelPast is a local-first platform for turning fragmented personal digital traces into a unified, explorable life timeline.

The system ingests heterogeneous sources such as:

- photos and videos
- calendars
- music listening history
- finance data
- trips and location history
- work activity
- sports and health data
- documents and emails

PixelPast is not a social product and not cloud-dependent by design. The core value is data ownership, reproducibility, and long-term explorable personal history.

## North Star

PixelPast should produce a coherent, queryable, visually understandable chronology of a person's life.

Every substantial design decision should be evaluated against these questions:

1. Does it improve temporal exploration?
2. Does it strengthen cross-source linking?
3. Does it preserve data ownership and reproducibility?
4. Does it keep the system maintainable and extensible long-term?

## Core Principles

- Local-first
- Full data ownership
- Reproducible ingestion
- Idempotent processing
- Modular source connectors
- Exploration over CRUD
- Visualization as a first-class feature
- Clarity over cleverness
- Determinism over magic

## Product Goal

The primary product goal is a zoomable, multi-year calendar heatmap inspired by the GitHub contribution grid.

Each day should be represented as an aggregated activity pixel and support drill-down into a detailed day-level storyline with cross-linked events.

## High-Level Architecture

The architecture is intentionally layered:

1. Ingestion Layer
2. Canonical Data Layer
3. Derived / Analytics Layer
4. API Layer
5. UI Layer

Primary data flow:

`Raw -> Canonical -> Derived`

### Ingestion Layer

Ingestion is modular and connector-based.

Each source connector should implement equivalent responsibilities for:

- discovery
- fetch
- transform
- persist

Ingestion jobs must be:

- idempotent
- independently executable
- runnable in full or incremental mode

Scheduling should initially remain simple, for example cron or systemd timers. Do not design around long-running thread-based monoliths.

### Canonical Data Layer

This is the relational core of the application. It should provide a stable shared model across all sources.

Core canonical entities:

- Event
- Asset
- EventAsset
- Tag
- EventTag
- AssetTag
- Person
- EventPerson
- AssetPerson
- PersonGroup
- PersonGroupMember
- Source
- ImportRun

Source-specific details may live in JSON/JSONB fields when necessary, but the canonical model should stay coherent and queryable.

### Derived / Analytics Layer

This layer contains computed views and summaries, not raw ingestion logic.

Examples:

- Daily aggregates
- Activity scores
- Heatmap data
- Cross-source correlations
- Higher-level inferred events such as vacations or business trips

### API Layer

The backend API is REST-first. GraphQL is optional later.

The API exposes canonical and derived data for the UI and other clients.

### UI Layer

The UI renders multi-scale temporal exploration views, especially:

- multi-year calendar grid
- month zoom views
- day drill-down views
- source and type filters

Business logic should not live in the UI.

## Architectural Constraints

These constraints are mandatory:

- Keep strict Raw -> Canonical -> Derived separation
- Do not put direct database logic inside connectors
- Do not access the database outside the service/repository boundary
- Do not introduce global mutable state
- Each source must be independently testable
- Connectors must not contain business logic

## Recommended Code Organization

Use package boundaries that reflect architectural roles, not vague buckets.

Avoid a single top-level `models/` directory. In this project, "model" can mean multiple different things:

- domain model
- database / ORM model
- API schema / DTO

Do not mix them.

### Model Placement Rules

Use explicit placement by responsibility:

- Domain entities and value objects belong in `domain/`
- ORM and persistence mappings belong in `persistence/` or `db/`
- API request and response schemas belong in `api/`

Practical guidance:

- Put business-facing entities such as `Event`, `Asset`, `Tag`, `Person`, `PersonGroup`, `Source`, `ImportRun`, and association entities in `domain/entities/`
- Put SQLAlchemy table mappings in `persistence/models/`
- Put repositories and transaction-facing persistence code in `persistence/repositories/` and related database modules
- Put Pydantic request/response models in `api/schemas/`
- Put connectors, ingestion pipelines, and ingest jobs in `ingestion/`
- Put derived-layer jobs and analytics logic in `analytics/` or a dedicated derived module
- Put cross-cutting helpers only in `shared/`, and keep that folder small

### Structure Philosophy

Prefer explicit names such as:

- `domain/entities`
- `persistence/models`
- `api/schemas`

over generic names such as:

- `models`
- `utils`
- `helpers`

If a folder name becomes ambiguous, rename it to express its role more precisely.

## Canonical Domain Model

PixelPast is fundamentally chronology-centered. Every primary entity in the system must be explicitly placed in time.

`Event` and `Asset` are both first-class temporal entities.

- `Event` represents a meaningful time-based occurrence in the life timeline
- `Asset` represents a stored digital object with its own capture or creation timestamp

They are related, but not identical, and must not be collapsed into a single concept too early.

### Source

Represents a data source.

Fields:

- id
- name
- type
- config (JSON)
- created_at

### ImportRun

Tracks the execution of ingestion jobs.

Fields:

- id
- source_id
- started_at
- finished_at
- status
- mode (`full` or `incremental`)

### Event

Represents a meaningful time-based occurrence in the life timeline, such as a calendar entry, trip, financial transaction, or music play.

Fields:

- id
- source_id
- type
- timestamp_start
- timestamp_end
- title
- summary
- latitude
- longitude
- raw_payload
- derived_payload
- created_at

Current event types include:

- calendar
- music_play
- financial_transaction

### Asset

Represents a stored digital object such as a photo, video, audio file, or document.

Fields:

- id
- external_id
- media_type
- timestamp
- latitude
- longitude
- metadata

Connectors should use `external_id` as a stable marker for recognizing previously imported objects.

### EventAsset

Optional association between a semantic event and a stored asset.

Fields:

- event_id
- asset_id
- link_type (`imported` or `derived`)

### Tag

Generic semantic annotation attachable to events and assets.

Fields:

- id
- label
- path
- metadata

Tags may be hierarchically nested through normalized paths, for example `activity/wedding/speech` or `travel/italy/venice`.

### EventTag

Associates events with tags.

Fields:

- event_id
- tag_id

### AssetTag

Associates assets with tags.

Fields:

- asset_id
- tag_id

### Person

Represents a known or inferred person.

Fields:

- id
- name
- aliases
- metadata

### EventPerson

Associates people with events.

Fields:

- event_id
- person_id

### AssetPerson

Associates people with assets.

Fields:

- asset_id
- person_id

### PersonGroup

Represents a named group of people.

Fields:

- id
- name
- type
- path
- metadata

Groups may be hierarchically nested through normalized paths.

### PersonGroupMember

Associates people with person groups.

Fields:

- group_id
- person_id

### DailyAggregate

Represents day-level derived summary data.

Fields:

- date
- total_events
- activity_score
- media_count
- music_count
- finance_count
- trip_count
- metadata

`DailyAggregate` is still intentionally provisional and should be refined when the first real analytics increments are implemented.

Design rule: keep `Event` and `Asset` independent in the core model and use explicit association entities where relationships exist. Add specialized tables only when concrete analytical needs justify them.

## Database Guidance

Initial database target:

- SQLite

Planned future targets:

- PostgreSQL
- MS SQL Server
- other relational engines when justified

Database expectations:

- relational schema
- JSON / JSONB support where available
- time-based indexes
- optional full-text search
- optional geospatial extensions later

Database conventions:

- store all timestamps in UTC
- allow JSON fields for extensibility
- avoid denormalization unless justified
- create indexes for `timestamp_start`, `source_id`, and `event.type`

## Backend Stack

Preferred backend stack:

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- Alembic
- Pydantic
- Typer
- pytest
- Ruff with Black-compatible formatting

## CLI Conventions

The CLI should be Typer-based and support independent execution of ingestion and derived jobs.

Canonical examples:

```text
pixelpast ingest <source>
pixelpast derive <job>
```

## Testing Expectations

Testing is required, especially around ingestion correctness.

Tests must cover:

- repeated execution
- empty sources
- error handling
- partial failures
- idempotent ingestion behavior

Recommended categories:

- unit tests for domain and service logic
- integration tests for persistence and API boundaries
- ingestion tests per connector

Each connector should be testable in isolation.

## API Guidance

The API should remain REST-first for now.

Prefer:

- clear read-oriented endpoints for timeline exploration
- endpoints for heatmap and day detail views
- explicit schemas for request and response bodies

Do not leak ORM models directly through the API.

## UI Core Principles

PixelPast is a visual exploration instrument centered around chronology.

The calendar grid is the primary projection surface and must always remain visible.
All contextual views (persons, tags, map, derived modes) react to the grid.

Two interaction layers exist:
- Hover = temporary contextual highlight
- Selection = persistent filtering and recoloring

The UI operates on timeline projections (not raw tables).
Simplicity and temporal clarity take priority over feature density.

## UI Guidance

The UI stack is expected to use:

- React
- TypeScript
- Tailwind
- D3 for heatmap visualizations

Do not move backend or canonical business logic into the UI.

## Roadmap Priorities

Near-term implementation priorities:

### Phase 0

- project structure
- database setup
- Alembic configuration
- core domain model
- CLI skeleton
- basic FastAPI setup
- ingestion worker coordinator / scheduler

### Phase 1

Initial ingestion workers:

- photo connector
- calendar connector
- media history connector

### Phase 2

Derived layer foundation:

- DailyAggregate job
- activity score calculation
- heatmap API endpoint

### Later Phases

Future areas include:

- finance, trip, email, document connectors
- cross-source analytics
- person linking
- location heatmaps
- full-text search
- embeddings / semantic search
- story mode
- performance hardening
- PostgreSQL migration
- monitoring ingestion workers from the UI
- agent-compatible MCP-style knowledge layer

## Contribution Rules

- Keep changes small and focused
- Separate migrations per schema change
- Avoid scope creep inside a task
- Favor maintainability and explicitness
- Reuse existing architectural boundaries instead of bypassing them

## Language and Repository Conventions

All checked-in artifacts should be in English, including:

- code
- comments
- documentation
- commit-relevant developer-facing text

If collaboration happens in another language, translate project artifacts to English before committing them.
