---
id: T045
title: INCIDENT — filter ± must change the number, not the operator
status: done
priority: 1
owner: Auto
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T041]
---

# T045 — − is 18→17, + is 18→19; at least / at most stay put

## Why

**Loop:** nudge floors after one-click.

1. Per-row **− / +** leave the displayed number unchanged (Age is at most **24** stays 24). Wiring: `applyDelta` then `valueControl = stepper`; the click writes onto a div and does not re-render filters. Footer **−1 / +1** do re-render, so they look like they work.
2. Footer **−1 / +1** currently loosen/tighten **by operator** (`gte` ∓, `lte` ±). User: if the num is **18**, **− → 17**, **+ → 19**, whether the row is at least or at most.

## Scope

- In: Per-row − and + change that row’s displayed number and the live table filter (Age input and HA 1–20 select)
- In: Footer **−1 / +1** apply **the same number delta** to every numeric row (`nudgeSquadHaFilterBy`): −1 → all numbers −1, +1 → all numbers +1. Do **not** flip by at least / at most. Skip text rows (Name / Squad / Personality / Media)
- In: Same clamps as `nudgeSquadHaFilterBy`
- Out: T044 (in_progress — do not steal). Suggest. New ops. Changing the operator

## Acceptance criteria

- [x] Age is at most 24 → row + shows 25 and the table uses 25; row − shows 23
- [x] DET is at least 18 → row − shows 17; row + shows 19
- [x] Footer −1 on a mix of at least 18 and at most 18 → both become 17; footer +1 → both become 19
- [x] Operators stay at least / at most
- [x] No Suggest changes

## Notes / pointers

- `renderSquadHaFilters` in `web/main.ts`: `applyDelta` then `valueControl = stepper`. Keep a stable ref to the input/select, or call `renderSquadHaFilters()` after nudge
- Footer today: `nudgeSquadHaFiltersByOp` (T041 loosen/tighten). Replace with a straight `delta` on each numeric filter (extend helper or map `nudgeSquadHaFilterBy`)
- Tests: `tests/squad-ha-table.test.ts` — lock 18 gte and 18 lte both −1 → 17

## Progress

- Per-row ± kept a stable `valueField` (input/select) so −/+ writes the number, then `renderSquadHaTable()`.
- Footer −1/+1 now `nudgeSquadHaFiltersBy` (same delta on every numeric row). `nudgeSquadHaFiltersByOp` removed. Text rows unchanged. Ops stay gte/lte.
- Verified: `npx vitest run tests/squad-ha-table.test.ts tests/mentoring.test.ts tests/mentoring-stack.test.ts` — 92 passed. T044 layout untouched.
