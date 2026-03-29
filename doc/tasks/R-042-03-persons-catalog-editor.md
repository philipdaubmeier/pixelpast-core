# R-042-03 - Persons Catalog Editor

## Goal

Implement the `Persons` section of the `Manage Data` workspace as an editable
catalog table with client-side quick search and section-batch save semantics.

## Dependencies

- `R-042-01`
- `R-042-02`

## Scope

### Load the Persons Catalog on Section Entry

When the user enters the `Persons` section, fetch the current persisted person
catalog through the dedicated manage-data endpoint.

The section should:

- show loading and error states through the shared overlay foundation
- own its current persisted snapshot
- derive an editable local draft from that snapshot

### Render an Inline-Editable Persons Table

Render the person catalog as an inline-editable table.

The editable columns are:

- display name
- aliases
- path

Inline editing should remain inside the table view rather than opening a
row-specific secondary dialog.

### Add Client-Side Quick Search

Provide one quick-search input above the table.

Search behavior:

- filter instantly in memory
- match across display name, aliases, and path
- operate on the full loaded section dataset

The first version may assume the catalog remains small enough for full
client-side filtering.

### Support Person Creation But Not Deletion

Expose a `+` action that appends a new editable person row to the local draft.

This task must not add delete support for persons.
If the UI later needs a delete affordance for layout consistency, it should be
visually absent or explicitly disabled.

### Persist the Persons Section as a Batch

Wire the section action bar so that:

- `Apply` saves the current person draft and keeps the section open
- `Save & Close` saves and closes the overlay
- `Discard` restores the last loaded persisted snapshot

After a successful save, reload the `Persons` section from the API.

## Out of Scope

- no person deletion
- no person merge flow
- no person-group membership editing from the persons table
- no server-side search

## Acceptance Criteria

- entering `Persons` loads the persisted person catalog
- the section renders an editable table for display name, aliases, and path
- quick search filters rows in memory across all three visible columns
- the section supports adding new person rows
- the section does not allow deleting persons
- apply, discard, and save-and-close are fully wired for the persons draft
- a successful save reloads the persisted persons catalog

## Notes

The person table should stay fast and direct.
This is catalog maintenance, not a form-heavy record detail workflow.
