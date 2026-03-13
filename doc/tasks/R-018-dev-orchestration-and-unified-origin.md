# R-018 - Dev Orchestration and Unified Origin

## Goal

Make the local development setup simpler and align it with the intended
deployment shape.

The current setup requires developers to know:

- that the React UI and Python API run as separate processes
- that they usually run on different ports
- that the UI must be pointed to the API explicitly or via fallback logic

This is workable for early increments, but it is not the most maintainable or
ergonomic direction.

The next step should make local development feel like one application while
also moving the repository toward the production model of one public origin
with path-based routing.

The preferred direction is:

- one development entrypoint that starts both UI and API
- one browser origin for the frontend during development
- one stable API prefix such as `/api`
- a deployment shape that can later sit cleanly behind a reverse proxy

---

## Scope

Implement a development and routing foundation that makes the application easier
to run locally and easier to deploy later.

### API Path Strategy

Move or expose the Python API under an explicit path prefix:

- `/api`

Preferred examples:

- `GET /api/exploration`
- `GET /api/days/context?start=<date>&end=<date>`
- `GET /api/days/{date}`
- `GET /api/health`

This should become the canonical public API shape for both development and
future deployment.

Avoid leaving the API at the root path long-term, because it makes reverse
proxy routing and static asset serving less explicit.

### Development Transport Strategy

Use the Vite development server as the browser-facing origin and proxy API
traffic to the Python backend.

Preferred direction:

- browser loads UI from `http://localhost:5173`
- UI issues requests to `/api/...`
- Vite proxies `/api` to the Python server, for example `http://127.0.0.1:8000`

Implications:

- the browser no longer needs to know the Python port directly in normal local
  development
- CORS complexity largely disappears for the common dev path
- the UI can use relative API paths by default in development
- local behavior becomes closer to reverse-proxy production behavior

Keep one explicit override path available for unusual setups if still needed,
but the default path should be zero-config for local development.

### Development Orchestration

Add one simple command that starts both the Python API and the Vite UI together.

Acceptable implementations include:

- a root-level Node script
- a Python-based dev runner
- a small shell orchestration command exposed through package scripts

The implementation should:

- start the Python API process
- start the UI development server
- forward logs clearly enough to see which process produced them
- shut both processes down cleanly on interruption

The command should be easy to discover and should not require developers to
manually manage two terminals for the common case.

Preferred developer experience:

```text
pixelpast dev
```

or:

```text
npm run dev
```

from the repository root, depending on which orchestration model is chosen.

### Documentation

Update the repository documentation so that local startup is unambiguous.

Document:

- the single recommended development command
- the fact that the UI uses `/api` in development
- the Python API port behind the proxy
- any optional override configuration

### Architectural Direction

This task should intentionally establish the path model that also works later
behind a real reverse proxy.

The intended later production shape is:

- one public base URL
- UI served at `/`
- API served at `/api`

Examples:

- `https://pixelpast.local/`
- `https://pixelpast.local/api/exploration`

The task does not need to implement full production deployment, but it should
make that deployment straightforward rather than introducing a dev-only pattern
that must later be undone.

---

## Out of Scope

- no authentication or session design work
- no container orchestration unless it is strictly required
- no production-ready nginx, Caddy, or Traefik setup in this task
- no TLS setup
- no full packaging or installer workflow
- no process supervision beyond what is needed for local development
- no frontend routing redesign
- no API contract redesign beyond introducing the `/api` prefix

---

## Acceptance Criteria

- the canonical API surface is available under `/api`
- the React UI uses `/api/...` requests in normal local development rather than
  directly targeting a different browser-visible origin
- Vite proxies `/api` requests to the Python backend during development
- developers can start the full local stack with one documented command
- stopping the orchestrator stops both child processes cleanly
- the setup works without requiring developers to manually set an API base URL
  for the default local case
- the repository documentation clearly explains the recommended startup flow
- the resulting routing shape matches the intended future deployment model of
  one origin with UI and API on separate paths

---

## Notes

This task is primarily about operational ergonomics and architectural
consistency.

Two principles should guide implementation:

1. Local development should feel like one application.
2. Local development should resemble production shape where practical.

Using a dev proxy plus an `/api` prefix is the simplest path that satisfies both.

Avoid overengineering this into a heavy orchestration framework.
The goal is a small, explicit, reliable setup that reduces friction.

If a configuration override remains available, treat it as an escape hatch, not
the primary path.
