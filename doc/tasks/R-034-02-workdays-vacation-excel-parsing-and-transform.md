# R-034-02 - Workdays Vacation Excel Parsing and Transform

## Goal

Parse the provided `.xlsx` workbook format for the new `workdays_vacation`
source and transform its populated day cells into canonical all-day `Event`
candidates.

This task replaces the earlier placeholder direction with a concrete
fixture-based import specification derived from:

- `test/assets/workday_vacation_test_fixture.xlsx`
- `test/assets/workday_vacation_test_fixture_markdown.md`

## Dependencies

- `R-034-01`
- `R-034`

## Scope

### Workbook Loading Direction

Use a robust Python `.xlsx` library for workbook parsing.

For this task, `openpyxl` is the intended library choice because the workbook
is a native Excel file and the parser must read typed cell values from the
first worksheet without requiring Excel itself to be installed.

The implementation should:

- open the workbook from the local filesystem
- always read the first worksheet, regardless of its sheet name
- treat the workbook structure, not the displayed title text, as the source of
  truth

### Source Identity Direction

One workbook file corresponds to one canonical `Source`.

The canonical source identity must be the normalized absolute path of the
workbook file. That path should be used as the stable unique recognition marker
for repeated imports of the same file.

The source persistence path should therefore treat the workbook absolute path as
the source `external_id`.

### Worksheet Structure Direction

The workbook uses a fixed matrix layout.

The parser must interpret the first worksheet as follows:

- rows `1` to `3` are non-data title area and must be ignored
- row `4` contains day-of-month headers in columns `E` through `AI`
- data rows begin at row `5`
- year anchor rows occur in column `B` at rows `12*n + 5`, i.e. `5`, `17`, `29`, ...
- column `C` contains the month anchor as an Excel date cell representing the
  first day of that month
- the usable day matrix spans:
  - rows `>= 5`
  - columns `E` through `AI`

The implementation should not rely on the worksheet title or any fixed literal
month names for parsing correctness.

### Year and Month Resolution Direction

Each data row belongs to one calendar month.

The represented year for a row is determined by the active year anchor in
column `B`:

- when a non-empty year appears in column `B`, it becomes the current year for
  that row and the following month rows until the next non-empty year anchor
- rows between year anchors inherit the most recent non-empty year from column
  `B`

The represented month for a row is determined from column `C`, which stores the
first day of the month as a typed Excel date value.

The parser should read column `C` as a date-like cell value, not as a rendered
label string.

The final represented date for one populated matrix cell is:

- `year` from the active column-`B` year anchor
- `month` from the column-`C` month anchor
- `day` from the row-`4` header of the current matrix column

If the month anchor from column `C` already carries a year value, the parser
should validate that it agrees with the active year anchor from column `B`.

### Legend Extraction Direction

Before reading the day matrix, the parser must build a code-to-meaning-and-
color mapping from the legend area.

The legend starts at row `5` and uses:

- column `AK` for the short code
- column `AL` for the human-readable meaning
- column `AW` for the hex color value

For each row `>= 5`:

- if column `AK` is non-empty after trimming, that row defines one legend entry
- the short code in `AK` is the lookup key
- the color in `AW` is required and must be a hex string beginning with `#`
- the description in `AL` may be preserved for diagnostics or future payload
  use, but it is not mapped into `Event.summary` in this task

The parser should ignore fully empty legend rows.

### Matrix Extraction Direction

After the legend is built, the parser must scan the usable day matrix in rows
`>= 5` and columns `E` through `AI`.

For each non-empty matrix cell:

- trim the cell text
- treat the trimmed text as the imported short code
- resolve the represented calendar date from year anchor, month anchor, and day
  header
- look up the code in the legend mapping

Each non-empty day cell represents one imported all-day event candidate.

Empty matrix cells do not create events.

### Day-Header Direction

The row-`4` headers in columns `E` through `AI` must represent calendar day
numbers `1` through `31`.

The implementation should validate that the header cells in that range are
usable day numbers.

If a header is malformed, the parser must fail explicitly rather than silently
misaligning dates.

### Invalid-Date Direction

The parser must handle month/day combinations deterministically.

If the matrix position implies an impossible date, for example day `31` in a
month with only `30` days:

- an empty cell at that position should simply be ignored
- a non-empty cell at that position must be treated as a transform error

### Canonical Event Mapping Direction

Each valid populated matrix cell becomes one canonical `Event` candidate with
the following required mapping:

- `source_external_id`
  - normalized absolute workbook path
- `external_event_id`
  - a stable day identity derived from the represented date
  - the preferred value is the ISO day string, for example `2025-01-06`
- `type`
  - `workdays_vacation`
- `timestamp_start`
  - represented day at `00:00 UTC`
- `timestamp_end`
  - following day at `00:00 UTC`
- `title`
  - the imported short code from the matrix cell
- `summary`
  - empty / `None`

The event must be modeled as an all-day event through the existing timestamp
range pattern rather than through any new canonical schema field.

### Payload Direction

`raw_payload` must preserve the direct color hex code resolved from the legend.

At minimum, `raw_payload` must contain:

- the resolved hex color value

It is acceptable to additionally preserve:

- the imported short code
- the legend description from column `AL`
- row and column traceability data
- the represented ISO date

`derived_payload` may remain empty for this task.

### Legend-Miss Validation Direction

If a non-empty matrix cell contains a short code that is not present in the
legend mapping, the transform must fail or surface an explicit transform error
for that workbook input.

The parser must not invent fallback colors and must not silently drop populated
cells with unknown codes.

### Persistence and Idempotency Direction

The resulting canonical candidates must support idempotent source-scoped
reconciliation.

The intended persistence behavior for repeated imports of the same workbook is:

- the workbook absolute path resolves the same canonical `Source`
- `external_event_id` identifies one source-local day event
- rereading an unchanged workbook produces no database writes
- a changed populated cell for an existing day updates only that matching event
- a newly populated cell inserts only that new event
- a day that was previously populated but is now empty is treated as
  missing-from-source and must be deleted for that source

This task therefore requires stable per-day event identity rather than
source-scoped full replacement.

## Out of Scope

- no database schema changes beyond what later tasks already cover
- no daily-aggregate derive behavior yet
- no exploration API changes yet
- no generalized spreadsheet-import abstraction beyond this workbook format

## Acceptance Criteria

- tests characterize `test/assets/workday_vacation_test_fixture.xlsx`
- the parser reads the first worksheet regardless of sheet name
- the legend mapping is extracted from `AK` / `AL` / `AW`
- populated day cells in `E:AI` rows `>= 5` become canonical
  `workdays_vacation` event candidates
- each candidate uses UTC midnight-to-midnight all-day timestamps
- `title` is the matrix short code and `summary` remains empty
- `raw_payload` preserves the legend hex color
- source identity is based on the workbook absolute path
- event identity is stable per represented day so unchanged rereads do not cause
  writes
- changed, newly added, and removed populated cells can be reconciled
  incrementally
- unknown legend codes and impossible populated dates fail explicitly

## Notes

The fixture characterization reveals one important validation concern:

- the visible matrix contains short codes such as `Sat` and `Sun`
- the extracted legend rows in `AK` / `AL` / `AW` currently expose only `O`,
  `V`, and `T`

This task therefore intentionally requires explicit handling of legend misses
instead of assuming every populated code is already covered. Legend misses
must result in a warning printed out to CLI and this day must be skipped,
not persisted.

That keeps the later implementation deterministic and makes any remaining
fixture inconsistency visible in tests instead of silently producing incomplete
derived data.
