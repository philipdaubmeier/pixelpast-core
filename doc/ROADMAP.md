# PixelPast – Roadmap (High-Level)

## Phase 0 – Foundation

- Project structure
- Database setup
- Alembic configuration
- Core domain model
- CLI skeleton
- Basic FastAPI setup
- Ingestion worker coordinator/scheduler

## Phase 1 – Initial Ingestion Workers

1. Photo Connector
   - NAS scan, EXIF extraction
   - optionally Lightroom Sqlite import
   - media Event creation

2. Calendar Connector
   - Outlook / ICS import
   - calendar Event creation

3. Media History Connector
   - Incremental Spotify/YouTube/etc. import
   - music_play Event creation

## Phase 2 – Derived Layer

- DailyAggregate job
- Activity score calculation
- Heatmap API endpoint

## Phase 3 – UI v1

- Multi-year heatmap
- Month zoom view
- Day detail view
- Event type filters

## Phase 4 – Additional Ingestion Workers

4. Finance Connector
   - QIF (Quicken Interchange Format) import
   - financial_transaction Event creation

5. Trip Connector
   - GPS data (google maps, owntracks, vehicle trip) import
   - trip Event creation

6. Email Connector
   - Import of emails
   - email Event creation

7. Document Connector
   - Import of letters and documents, OCR and infer receive date
   - document Event creation

## Phase 5 – Analytics in Derived Layer

- Analyze, crosscorelate data and derive higher level events like vacations or business trips out of combinations of trip data, calendar data, photo data and others

## Phase 6 – Extensions

- Person linking
- Location heatmaps
- Full-text search
- Embeddings / semantic search
- Cross-source correlation engine
- Story mode

## Phase 7 – Hardening

- Performance optimization
- Index tuning
- PostgreSQL migration (from SQLite)
- Backup strategy
- Monitoring of ingestion workers from UI

## Phase 8 – Even more Ingestion Workers

- Messenger (WhatsApp/Signal/Telegram metadata) import
- GitHub Commits
- Home Assistant events (Motion sensors, actuator events)
- Even more smarthome: heating, photovoltaics, power consumption
- Health (Strava, Garmin, Google Fit - Heartrate, Steps)
- Weather history (via public APIs)
- News of the day (via public sources)

## Long-Term Goal

A personal, agent-compatible (MCP) knowledge layer
over one’s own life.