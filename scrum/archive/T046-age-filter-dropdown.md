---
id: T046
title: Age filter uses the same number dropdown as HAS / attrs
status: done
priority: 2
owner: Auto
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T045]
---

# T046 — Age value is a select, not a number input

## Why

Age is the only numeric filter that uses `<input type="number">` (browser spinner). HAS and DET…CON use a dropdown. User: same num dropdown for Age. Dual steppers (native arrows + −+) are the extra noise.

T039 “not capped at 20” still holds: Age options are the existing Age band (0–50), not 1–20.

## Scope

- In: Age filter value control = same `<select>` pattern as HAS / attributes, options = `squadHaNumericFilterBounds("age")` (inclusive)
- In: Per-row −/+ and footer −1/+1 still change Age the same as other numeric rows
- Out: Capping Age at 20. Free-typed Age. Ranker page. Suggest

## Acceptance criteria

- [x] Age is at most 24 is a dropdown showing 24 (no browser up/down inside the field)
- [x] Dropdown includes ages outside 1–20 (e.g. 24, 33); 20 is not the max
- [x] Row − / + and footer −1 / +1 still move Age 24 → 23 / 25
- [x] One-click Age floors still write into that dropdown

## Notes / pointers

- `renderSquadHaFilters` in `web/main.ts`: `if (ageKey)` builds `input type="number"`; other numerics `fillSelect` 1–20
- Bounds: `SQUAD_HA_AGE_FILTER_MIN/MAX` in `web/squad-ha-table.ts` (0–50)

## Progress

- Age HA filter is the same `<select>` as HAS / DET…CON. Options from `squadHaNumericFilterValueOptions("age")` = 0–50 inclusive (24, 33 in list; 20 not max). HAS/DET stay 1–20.
- Removed Age `input type="number"`. Per-row −/+ and footer −1/+1 still `nudgeSquadHaFilterBy` (24 → 23 / 25). One-click floors (22 / 33) are options on that select.
- Ranker page untouched. Verified: `npx vitest run tests/squad-ha-table.test.ts tests/mentoring.test.ts tests/mentoring-stack.test.ts` — 95 passed.
