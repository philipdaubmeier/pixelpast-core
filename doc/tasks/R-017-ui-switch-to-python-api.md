# R-017 - UI Switch to Python API

## Goal

Switch the React UI from local runtime mocks to the Python API.

The current interaction model should remain intact while the transport moves to
real HTTP-backed projection endpoints.

---

## Scope

Replace the current mock-backed timeline API wiring with HTTP calls to:

- `GET /exploration`
- `GET /days/context?start=<date>&end=<date>`

Update the UI so that:

- calendar math remains client-side
- `year`, `weekIndex`, and `weekdayIndex` are derived from `date`
- map positioning math is performed in the UI from API `latitude` and
  `longitude`
- transport DTOs are separated from render projections
- initial shell loading states are explicit
- hover context loading and failure states are explicit
- hover context is prefetched for the currently visible date window rather than
  fetched one day at a time per mouse movement
- the UI keeps a local cache for already loaded day-context ranges

Use one explicit development transport path.

Preferred direction:

- `VITE_PIXELPAST_API_BASE_URL`
- FastAPI CORS support for local UI development

Runtime cleanup:

- remove TypeScript runtime mock imports from the live app path

---

## Out of Scope

- no major visual redesign
- no move of calendar math into the backend
- no map library adoption
- no day detail page
- no server-driven pagination work in this task
- no advanced caching framework unless it is strictly required

---

## Acceptance Criteria

- the UI boots from the Python API instead of local runtime mocks
- the multi-year grid still renders correctly
- persistent person and tag filters still recolor the grid
- hover still updates the persons, tags, and map panels
- hover interaction does not issue one HTTP request per hovered day
- the UI can preload and reuse hover context for the visible calendar range
- the map panel renders from API coordinates rather than mock `x` and `y`
- the live app no longer imports runtime data from `ui/src/mocks/timeline.ts`
- local development can connect the UI to the Python API with one explicit
  configuration path

---

## Notes

Keep the existing interaction model stable while changing the transport layer.
Prefer a small and explicit HTTP client over hiding the integration behind
unnecessary abstraction.

The intended v1 strategy is bounded range preload plus client-side caching.
Do not translate pointer movement directly into one request per pixel or day.
