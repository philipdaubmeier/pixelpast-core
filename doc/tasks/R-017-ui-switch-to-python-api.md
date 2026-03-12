# R-017 - UI Switch to Python API

## Goal

Switch the React UI from local runtime mocks to the Python API.

The current interaction model should remain intact while the transport moves to
real HTTP-backed projection endpoints.

---

## Scope

Replace the current mock-backed timeline API wiring with HTTP calls to:

- `GET /exploration`
- `GET /days/{date}/context`

Update the UI so that:

- calendar math remains client-side
- `year`, `weekIndex`, and `weekdayIndex` are derived from `date`
- map positioning math is performed in the UI from API `latitude` and
  `longitude`
- transport DTOs are separated from render projections
- initial shell loading states are explicit
- hover context loading and failure states are explicit

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
- no advanced caching framework unless it is strictly required

---

## Acceptance Criteria

- the UI boots from the Python API instead of local runtime mocks
- the multi-year grid still renders correctly
- persistent person and tag filters still recolor the grid
- hover still updates the persons, tags, and map panels
- the map panel renders from API coordinates rather than mock `x` and `y`
- the live app no longer imports runtime data from `ui/src/mocks/timeline.ts`
- local development can connect the UI to the Python API with one explicit
  configuration path

---

## Notes

Keep the existing interaction model stable while changing the transport layer.
Prefer a small and explicit HTTP client over hiding the integration behind
unnecessary abstraction.
