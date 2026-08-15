---
id: T060
title: Footer ± skips Age
status: done
priority: 1
owner: auto
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T047]
---

# T060 — Footer −1/+1 does not move Age

## Why

Footer ± is the attribute-wide loosen/tighten (DET/HAS/CON, CON inverted). Age is the T039 mentor/mentee gate, not an HA attr. After one-click, loosen-all currently nudges Age too and undoes the floor. Documented loop: click player → footer ±.

## Scope

- In: `nudgeSquadHaFiltersBy` skips `key === "age"` (value and op unchanged)
- In: Per-row Age **+ / −** still ±1 (T045)
- Out: Skipping HAS or other numeric rows. Changing CON invert (T047). Changing operators. Suggest

## Acceptance criteria

- [x] Age is at least 21 + footer **+1** → Age still **21**; DET ≥ 18 → **19**
- [x] Age is at most 24 + footer **−1** → Age still **24**; DET ≥ 18 → **17**
- [x] Age row’s own **+** → 22 / 25, **−** → 20 / 23
- [x] CON invert unchanged (CON ≤ 18 + footer **+1** → **17**)

## Notes / pointers

- `nudgeSquadHaFiltersBy` in `web/squad-ha-table.ts` — skip Age; still invert Controversy
- T047 AC “Age follows footer number” is superseded
- Tests: `tests/squad-ha-table.test.ts` (kid one-click footer case currently expects Age to move)

## Progress

- `nudgeSquadHaFiltersBy` returns Age filters unchanged (value and op). Per-row still `nudgeSquadHaFilterBy` ±1. CON invert unchanged.
- T045 footer test uses HAS for lte number-delta (Age is no longer a footer target). Kid one-click footer −1 keeps Age ≥ 22.
- Verified: `npx vitest run tests/squad-ha-table.test.ts` — 58 passed (Age ≥ 21 + footer +1 → 21 / DET 19; Age ≤ 24 + footer −1 → 24 / DET 17; Age row ±; CON ≤ 18 + footer +1 → 17).
