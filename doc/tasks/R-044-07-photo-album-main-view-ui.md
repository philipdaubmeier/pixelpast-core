# R-044-07 - Photo Album Main-View UI

## Goal

Add the `Photo Album` main view to the app shell and implement the three-column
album-browsing experience on top of the new backend contracts.

This task makes the new projection usable in the frontend without weakening the
existing shared filter and interaction model.

## Dependencies

- `R-035`
- `R-044-04`
- `R-044-05`
- `R-044-06`

## Scope

### Add `Photo Album` To Main-View Navigation

The app shell should expose `Photo Album` as a peer main view next to
`Day Grid` and `Social Graph`.

Required outcomes:

- main-view switching preserves global persistent filters
- leaving the album view tears down heavy view-local work cleanly
- returning to the album view can restore useful local selection state where it
  is practical

### Implement The Left Navigation Column

The left column should present two explicit tree sections:

- `Folders`
- `Collections`

The UI should support:

- tree expansion and collapse
- node selection
- parent-node aggregate selection
- loading and empty states

### Implement The Center Album Surface

The center column should support two states:

- album mode
  - thumbnail grid for the selected folder or collection
- asset focus mode
  - larger selected photo while keeping both side columns visible

The grid should load thumbnail data from the album-listing API and open the
original image only when the user selects an asset.

### Reuse Shared Right-Column Controls

The right column should reuse the existing people, tag, and map controls rather
than introducing album-specific variants.

Required interaction rules:

- selected album loads stable context from the album-context API
- thumbnail hover highlights related context locally without layout movement
- clicking people or tags mutates the shared persistent filters

### Implement Selected-Asset Detail Loading

When the user selects an asset, the UI should:

- load the single-photo detail payload lazily
- render richer metadata in the right column
- optionally render face-region overlays over the selected image

The UI should degrade cleanly when optional metadata or face regions are
missing.

## Out of Scope

- no metadata editing UI
- no collection-management UI
- no bulk actions
- no slideshow or full-screen gallery mode

## Acceptance Criteria

- `Photo Album` is available as a main view in the app shell
- the UI exposes separate `Folders` and `Collections` trees
- selecting a folder or collection loads a thumbnail album in the center column
- parent-node aggregate selection works in the navigation tree
- the right column reuses shared controls and shared persistent filters
- single-photo detail loads lazily and can render optional face-region overlays
- thumbnail hover highlights context without panel replacement or layout jumps

## Notes

The quality bar for this task is product coherence. The album view should feel
like another projection of the same PixelPast system, not like a standalone
media manager embedded beside it.
