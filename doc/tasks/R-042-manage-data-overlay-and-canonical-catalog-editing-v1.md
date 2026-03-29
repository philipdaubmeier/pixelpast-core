# R-042 - Manage Data Overlay and Canonical Catalog Editing v1

## Goal

Introduce a first minimal `Manage Data` workspace for manual maintenance of the
canonical person and person-group catalogs.

This is not a general settings system.
It is a focused data-management surface for canonical records that already
exist in the relational core but currently lack a dedicated UI and mutation
path.

The new surface should open from a subdued `Manage` button in the top-right app
shell area and present a full-screen workspace overlay with explicit
section-based editing.

The first version should support:

- browsing and editing canonical `Person` rows
- browsing, creating, editing, and deleting canonical `PersonGroup` rows
- editing membership for one `PersonGroup`
- client-local draft editing with explicit section-scoped save actions
- fresh section loading on entry instead of one large bootstrap payload

## Dependencies

- `R-035`

## Scope

This task series introduces a new manage-data vertical slice across UI, API,
and persistence.

### Manage Data Workspace Overlay

Add a dedicated `Manage` action to the app shell and use it to open a
full-screen workspace overlay.

The overlay should:

- feel like a temporary management workspace above the exploration product
- not become a third long-lived main view
- expose a left-side section list
- render the active editor in a large right-side content region
- own explicit close, discard, apply, and save-and-close actions

The initial section list is:

- `Persons`
- `Person Groups`

### Section-Scoped Draft Editing

Each section should load its own data freshly when the user enters it.

Within a section:

- data may be searched, edited, and staged fully client-side
- no row-level keystroke editing should call the API directly
- save operations should submit the current section draft as one batch payload
- closing the overlay or switching sections with unsaved changes should require
  an explicit discard-or-save decision

After a successful save, the section should reload from the API so the client
draft realigns with persisted truth.

### Persons Catalog Editing

The `Persons` section should provide a client-filtered editable table with:

- display name
- aliases
- path

Behavior:

- quick search filters instantly across all visible person columns
- the whole person catalog may be loaded into memory for client-side filtering
- rows may be edited inline
- new persons may be added through a `+` action
- person deletion is intentionally forbidden in v1

Canonical contract direction:

- aliases should be treated as an explicit string list in API contracts
- path uniqueness should be validated server-side

### Person Groups Catalog Editing

The `Person Groups` section should provide a similar client-filtered table.

The first version should include:

- editable group display name
- read-only member count
- create action
- delete action with explicit confirmation
- per-row action to enter a dedicated membership-management subview

For v1, `PersonGroup.type` should remain out of the UI and be owned
server-side as a fixed manual-management value.

### Person Group Membership Editing

Membership editing should happen in a dedicated group-focused subview inside
the overlay.

The subview should support:

- loading the persisted current members for one group
- adding members through a person search input with dropdown suggestions
- confirming an add via click or enter
- removing members through explicit row actions
- saving the group membership as one replacement batch

The picker should use persisted persons only.
Unsaved new persons from the `Persons` section are intentionally unavailable
until that section has been saved and reloaded.

## Subtasks

- `R-042-01` - Manage Data overlay shell and client draft foundation
- `R-042-02` - Manage Data API contracts and catalog persistence foundation
- `R-042-03` - Persons catalog editor
- `R-042-04` - Person Groups catalog editor
- `R-042-05` - Person Group membership editor

## Out of Scope

- no generic application settings system
- no `Appearance` or `Language` sections
- no authentication or role model
- no person deletion
- no person merge or deduplication workflow
- no group hierarchy editor
- no server-side search or pagination for these catalogs in v1
- no one-shot bootstrap payload for all manage-data sections
- no cross-section bulk save spanning persons and groups together
- no editing of tags, places, sources, or other canonical catalogs in this
  series

## Acceptance Criteria

- the top bar exposes a subdued `Manage` action on the far right
- the action opens a full-screen manage-data workspace overlay
- the overlay exposes `Persons` and `Person Groups` as explicit sections
- each section loads its data freshly on entry
- each section keeps edits locally until the user explicitly applies or saves
- `Persons` supports inline editing of display name, aliases, and path
- `Persons` supports creation but not deletion
- `Person Groups` supports creation, rename, deletion, and member-count display
- `Person Groups` exposes a dedicated membership-management subview
- group membership can be added and removed through a persisted-person picker
- section save operations are batch-oriented and realign the client by
  reloading persisted state afterward

## Notes

This series deliberately starts with catalog maintenance only.
It should not drift into a general-purpose preferences framework.

The design intent is:

- quiet shell entry point
- full-screen workspace when active
- explicit drafts
- explicit save semantics
- clean separation between catalog editing and exploration
