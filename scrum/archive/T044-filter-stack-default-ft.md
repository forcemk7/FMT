---
id: T044
title: One filter per line; Add filter defaults to Squad FT
status: done
priority: 2
owner: Auto
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T043]
---

# T044 — Stack filters; Add starts at Squad = FT

## Why

T043 wrap puts two chips on a line so AND joins and key names are hard to scan (user: one filter per line for overview). **+ Add filter** currently inserts Personality. User wants the new row to be **Squad = FT** so they can narrow the club-wide table without picking the key first.

## Scope

- In: Squad HA filter list is **one filter per line** (column). Keep T043 shrink-to-content (do not stretch the row across the panel). AND/OR sits between lines
- In: **+ Add filter** inserts `unit` **eq** **FT** (label Squad). User can change key/value after. Does **not** change one-click preset rows
- Out: Ranker page. Auto-applying Squad FT on kid/senior click (that would hide II/U19 mentors — T035). Suggest. New ops

## Acceptance criteria

- [x] Ten one-click filters stack as ten lines, not two columns
- [x] Each line is only as wide as its controls (value then −+ still together)
- [x] Empty filters → Add filter → one row: Squad is FT; table shows FT only until that row is changed or cleared
- [x] One-click kid/senior preset is unchanged (no extra Squad row)
- [x] Clear All still empties everything

## Notes / pointers

- Wrap lives on `#squad-filter-rows { flex-direction: row; flex-wrap: wrap }` in `web/styles.css` (T043)
- Default insert: `newSquadHaFilter()` in `web/main.ts` — today `personality` / `eq`
- Unit values: `FT` / `II` / `U19` (`SQUAD_HA_UNIT_ORDER`)

## Progress

- Shipped: `#squad-filter-rows` is column, `align-items: flex-start`; T043 `width: max-content` kept. AND/OR stays a sibling between rows.
- `newSquadHaManualFilter` inserts `unit` eq `FT`. One-click still `squadHaClickPreset` (no Squad row). Clear All unchanged.
- Verified: `npx vitest run tests/squad-ha-table.test.ts` (38 passed); `tsc --noEmit` clean.
