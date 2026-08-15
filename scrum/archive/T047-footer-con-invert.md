---
id: T047
title: Footer ± inverts Controversy only
status: done
priority: 2
owner: Auto
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T045]
---

# T047 — Footer +/− flips CON; row +/− does not

## Why

CON is lower-is-better. T045 made footer **−1 / +1** a straight number delta on every numeric row, so CON moves with DET. After a kid one-click (DET ≥, CON ≤), footer **−** loosens DET but **tightens** CON. User: keep per-row ± normal; invert **only Controversy** on the footer.

## Scope

- In: Footer **+1**: DET/Age/HAS/… **+1**, Controversy **−1**. Footer **−1**: opposite. Clamp unchanged
- In: Per-row CON **+ / −** stay **+1 / −1** (not inverted)
- Out: Inverting Age or any other at-most row. T046 (in_progress — do not steal). Suggest. Changing operators

## Acceptance criteria

- [x] CON is at most 18 + footer **+1** → CON **17**; DET is at least 18 → **19**
- [x] Same mix + footer **−1** → CON **19**, DET **17**
- [x] CON row’s own **+** → 19, **−** → 17
- [x] Age is at most 24 still follows the footer number (24 → 23 on −1), not the CON invert

## Notes / pointers

- `nudgeSquadHaFiltersBy` in `web/squad-ha-table.ts` — apply `-delta` when `filter.key === "controversy"`
- Per-row still `nudgeSquadHaFilterBy(filter, ±1)`
- Tests: `tests/squad-ha-table.test.ts`

## Progress

- Footer `nudgeSquadHaFiltersBy` applies `-delta` when `filter.key === "controversy"`. Per-row still `nudgeSquadHaFilterBy(filter, ±1)` (CON 18 → 19 / 17). Age and other at-most rows still follow the footer number.
- Clamp unchanged. Operators unchanged. T046 not touched.
- Verified: `npx vitest run tests/squad-ha-table.test.ts` — 47 passed (CON ≤ 18 + footer +1 → 17 / DET ≥ 18 → 19; footer −1 → CON 19 / DET 17; Age ≤ 24 footer −1 → 23).
