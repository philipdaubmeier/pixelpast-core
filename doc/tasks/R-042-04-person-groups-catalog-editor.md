# R-042-04 - Person Groups Catalog Editor

## Goal

Implement the `Person Groups` section of the `Manage Data` workspace as an
editable catalog table with group creation, rename, deletion, and entry into a
dedicated membership-management subview.

## Dependencies

- `R-042-01`
- `R-042-02`

## Scope

### Load the Person-Group Catalog on Section Entry

When the user enters the `Person Groups` section, fetch the current persisted
group catalog through the dedicated manage-data endpoint.

The section should own:

- the persisted catalog snapshot
- a local editable draft
- loading, empty, and error states

### Render the Group Catalog as an Editable Table

Render the group catalog in a table shaped similarly to the persons editor.

The first version should include:

- editable display name
- read-only member count
- create action
- delete action
- per-row membership-edit action

The table should stay inline-editable.
Do not route basic group rename through a separate form view.

### Add Client-Side Quick Search

Provide one quick-search input above the table.

The first version may filter fully in memory across the loaded group catalog.
At minimum, search should match group names.

### Support Group Deletion With Explicit Confirmation

Deleting a group is allowed in v1, but it should remain a clearly destructive
action.

The UI should:

- require explicit confirmation
- remove the row from the local draft only after confirmation
- persist the delete through the section-batch save path

The deletion semantics remain limited to the group row and its membership links.

### Preserve a Clear Path Into Membership Editing

Each row should expose an explicit entry point into the dedicated membership
editor introduced later in the series.

This task should establish that navigation affordance and preserve the selected
group context needed by the membership task.

## Out of Scope

- no membership editor implementation in this task
- no group hierarchy editing
- no editing of server-owned group type

## Acceptance Criteria

- entering `Person Groups` loads the persisted group catalog
- the section renders an inline-editable table with group name and member count
- quick search filters the loaded group catalog in memory
- the section supports creating new groups
- the section supports deleting groups with explicit confirmation
- each row exposes a membership-edit entry point
- apply, discard, and save-and-close are wired for the group catalog draft

## Notes

This task should keep the catalog editor lightweight.
Detailed membership management belongs in the dedicated subview, not in crowded
inline table cells.
