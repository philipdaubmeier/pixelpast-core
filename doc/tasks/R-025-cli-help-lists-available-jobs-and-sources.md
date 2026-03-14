# R-025 - CLI Help Lists Available Jobs and Sources

## Goal

Improve the CLI help output so users can discover supported operational targets
without triggering a failing command invocation.

`pixelpast derive --help` must list all supported derive jobs, and
`pixelpast ingest --help` must list all supported ingest sources.

## Dependencies

- `R-004`

## Scope

### Expose Supported CLI Targets Explicitly

Refine the CLI command surface so the help text for `ingest` and `derive`
includes the currently supported targets.

This should cover:

- supported ingest sources such as `photos`
- supported derive jobs such as `daily-aggregate`
- a single obvious place where the CLI can obtain these supported values

The implementation should avoid duplicating target lists across help text,
validation logic, and command dispatch.

### Keep Command Dispatch Consistent

The current runtime behavior for executing sources and jobs must remain intact.

Improving help output must not weaken:

- unsupported-target validation
- explicit exit codes
- thin CLI orchestration boundaries

### Add CLI Regression Tests

Extend the CLI test suite so help output is asserted directly.

At minimum, tests should verify:

- `pixelpast ingest --help` mentions every supported ingest source
- `pixelpast derive --help` mentions every supported derive job
- unsupported sources and jobs still fail with the expected invalid-argument
  behavior

## Out of Scope

- no new ingest connectors
- no new derive jobs
- no redesign of the operational command hierarchy

## Acceptance Criteria

- `pixelpast ingest --help` lists all supported ingest sources
- `pixelpast derive --help` lists all supported derive jobs
- the supported target lists come from a shared authoritative registration point
- unsupported targets still return the invalid-argument exit code
- automated CLI tests cover the help output contract

## Notes

Typer does not automatically document arbitrary string arguments as enumerated
values when command dispatch happens manually. The solution should make the
available targets visible in help output without forcing business logic into the
CLI layer.
