---
id: T042
title: INCIDENT — drop nameless FT ghost row from HA table
status: done
priority: 1
owner: worker
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: []
---

# T042 — No name, no HA row

## Why

**Loop:** club HA table is the squad you mentor from. User: leftover row, Unit **FT**, Name/Age/Personality/Media/HA all **—**. Status already counts it (`84/85 mentoring-ready · 1 name missing`). Mentoring pool already skips unnamed (`candidateFromRosterPlayer`). The table still paints the ghost job. You cannot check suitability or capture a unit with no name and no numbers.

## Scope

- In: Club Personalities HA table omits rows with no resolved name (`rosterResolvedName` null / empty). Same rule as Mentoring pool
- In: Named players with some `—` cells still show (Gilson-class missing Det/Lea is not this bug)
- Out: Extract / namelist RE (T008). Do not hunt the ghost job unless hiding the row is not enough. Suggest. T040/T041 reopen. CA/PA. Hiding named players who have attrs

## Acceptance criteria

- [x] The dash-only FT row is gone from the club HA table
- [x] Named FT / II / U19 rows unchanged (including cells that are honestly `—`)
- [x] Trust bar may still say `1 name missing` (extract hole stays visible; T011)
- [x] No Suggest changes

## Notes / pointers

- `buildSquadHaRow` sets `name: resolvedName ?? ""` and still emits a row; `mergeClubWideAtClubPlayers` only requires a finite `uid`
- `isRosterNameResolved` / `rosterResolvedName` in `web/extract-trust.ts`
- Tests: `tests/squad-ha-table.test.ts` — nameless uid must not be visible; named + missing Det still visible
- User GT screenshot: last row Unit FT, everything else `—`

## Progress

- Club HA table skips unresolved names (`isRosterNameResolved`: empty / `uid:` / `job:`) in `mergeClubWideAtClubPlayers`; `buildSquadHaRow` returns null if no resolved name.
- Named FT/II/U19 still merge; Gilson-class missing Det/Lea still paints `—`.
- Trust bar still uses `clubAllPlayers()` / T011 (name-missing hole stays). No Suggest edits.
- Verified: `npx vitest run tests/squad-ha-table.test.ts tests/extract-trust.test.ts` — 41 passed.
