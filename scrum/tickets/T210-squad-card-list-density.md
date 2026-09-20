---
id: T210
title: Squad — card / list density toggle
status: deferred
priority: null
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T209]
---

# T210 — Squad — card / list density toggle

## Why

Wanted: denser “row with columns” scan beside the existing card matrix, toggled from the Squad toolbar (right of status control). Spreadsheet-replace energy — but Loop A already opens the desk from cards. **Not need-to-have while usage holds.** On the board so the ask is tracked; do not claim until HQ unfreezes.

## Scope (when unfrozen)

- In: Toolbar control to the right of roster status (T209): toggle **Cards** vs **List**
- In: List = same player signals as cards, laid out as compact rows/columns (still clickable into the desk) — not a second product table
- In: Persist preference for the session (or existing desk-session helpers) if cheap; otherwise default Cards
- Out: Replacing cards entirely; sortable columns; Loans / GM / HoYD density; new extract / RE

## Acceptance criteria (when unfrozen)

- [ ] Toggle switches Squad desk between card matrix and row layout without changing filter/team selection
- [ ] Both layouts open the same player desk path
- [ ] One commit `T210: …`

## Notes / pointers

- UI today: `SquadPlayerCard` + `squad-position-matrix` in `desktop/src/components/my-team-screen.tsx`
- Prefer reusing card metrics (face, name, CA/PA/HAS rings) in a horizontal row — no parallel data model
- HQ gate (2026-09-04): deferred — dual-layout tax; revisit if card scan fails the sheet-replace loop

## Progress

Deferred — not ready to claim.
