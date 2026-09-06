---
id: T239
title: Lock attr desk row metrics (no Δ layout shift)
status: done
priority: 2
owner: auto
claimed_at: "2026-09-06T19:25:00+02:00"
started_at: "2026-09-06T19:25:00+02:00"
completed_at: "2026-09-06T20:09:00+02:00"
depends_on: []
---

# T239 — Lock attr desk row metrics (no Δ layout shift)

## Why

Outfield↔Outfield and GK↔GK profile hops showed a vertical layout shift on Attributes (and Development) when recent Δ badges appeared. Loop A desk must stay stable while browsing the squad.

## Scope

- In: Fixed values/Δ column widths; Δ slot height = value line box; restore legacy GS span reset so padding cannot stack; `has-delta-col` on rows; dossier fills remaining height without stretching row gaps
- Out: Unifying GK vs outfield desks; name ellipsis; Match experience work

## Acceptance criteria

- [x] Within-role player hops do not change attribute row vertical spacing when Δ appears/disappears
- [x] Δ uses the same type metrics as values and cannot inflate row height
- [x] Row packing is not spaced out by legacy `.attribute-column span` padding
- [x] One commit `T239: …`

## Progress

- Root cause: Δ in an `auto` values track + legacy GS `span { padding:3px 0; display:flex }` restacked when desk primitives were excluded from the reset
- Shipped: fixed `--attr-values-width` track (in tree via T238 CSS), fixed-height Δ slot, reset-then-reapply desk chrome, `has-delta-col` on AttrRow
- Verified: code path review; user confirmed prior spacing regression and asked for ship
- Commit: `32c04621cfedada0c15e12770faf6279448f925f`
