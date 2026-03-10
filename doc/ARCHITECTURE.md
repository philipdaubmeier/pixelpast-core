# PixelPast – Architecture

## High-Level Components

1. Ingestion Layer
2. Canonical Data Layer
3. Derived / Analytics Layer
4. API Layer
5. UI Layer

---

## 1. Ingestion Layer

Modular connector-based architecture.

Each source implements:

- discover()
- fetch()
- transform()
- persist()

Jobs must be:

- Idempotent
- Independently executable (CLI)
- Runnable in "full" or "incremental" mode

Scheduling (initially):
- systemd timers or cron

No long-running thread-based monoliths.

## 2. Data Architecture

Pattern: Raw → Canonical → Derived

### Raw Layer
- Storage of original payloads (JSON)
- Import run tracking

### Canonical Layer
Relational core model:
- Event
- Asset
- Person
- Location
- Source

JSON/JSONB fields allowed for source-specific metadata.

### Derived Layer
- Daily aggregates
- Activity scores
- Heatmap data
- Cross-source correlations

## 3. Database

Initial:
- SQLite

Target:
- PostgreSQL, MS SQL Server etc.

Features:
- Relational schema
- JSON/JSONB support
- Time-based indexes
- Optional full-text search
- Optional PostGIS for geospatial data

## 4. API

Backend stack:
- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- Alembic
- Pydantic

API Style:
- REST-first
- GraphQL optional later

## 5. UI

- React + TypeScript
- Tailwind
- D3 for heatmap visualizations

Core features:
- Multi-year calendar grid
- Zoom levels
- Day drill-down view
- Filters by source, person, type

## 6. Deployment

- Docker optional
- Single VM (homelab) compatible
- Separate logical services:
  - API
  - Worker CLI
  - Database

## 7. Architectural Constraints

- No business logic in the UI
- No direct DB logic inside connectors
- No global mutable state
- Each source must be independently testable