---
id: T048
title: Restore per-player HA progress (evolution pane)
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: []
---

# T048 — Put the attribute-progress tool back on the navigator

## Why

**Loop:** see personality HA **shift** after mentoring in FM. User: **Yoan Robert** personality (and maybe media handling) changed — change is good — but T035 collapsed unit tabs and left `#squad-evolution` behind `squadUnitView === "attributes"` with **no tab**. A one-off worker A/B of Yoan Robert does not restore the loop.

The pane already exists (CA history + personality pack snapshots on upload). Open the door.

## Scope

- In: Navigator **Personalities | Progress | Loans | Mentoring** (or equivalent). Progress shows the existing `#squad-evolution` pane
- In: Player picker = club-wide at-club named players (same pool as the HA table), not FT-only `activeSquadPlayers()` leftover
- In: Hash/deep-link so Progress stays Progress on refresh
- Out: New charts. Worker mission to identify Yoan Robert’s delta. Suggest. CA/PA zoo. Talent. Rebuilding FM’s mentoring screen

## Acceptance criteria

- [x] User can open Progress without a hidden hash and pick **Yoan Robert**
- [x] Personality-pack / general HA series from existing history still plot when snapshots exist
- [x] Personalities table, Loans, Mentoring unchanged in purpose
- [x] No Suggest changes

## Notes / pointers

- Pane: `#squad-evolution` in `web/index.html`. Render: `renderSquadEvolution()` / `populateSquadEvolutionPlayers()` in `web/main.ts` — gated on `squadUnitView === "attributes"`
- HA snapshots: `web/ha-history-store.ts` (upload-keyed; no in-save CA strip for pack)
- Combo labels come from current extract; history is pack numbers. Do not invent a second personality-name time series this ticket
- T035 hid FT/II/U19 tabs on purpose — do not bring those back

## Progress

- Navigator is Personalities | Progress | Loans | Mentoring. Progress shows existing `#squad-evolution` (no new charts; FT/II/U19 tabs stay hidden).
- Player picker uses `mergeClubWideAtClubPlayers` (same named at-club pool as the HA table), so a U19/II name like Yoan Robert is pickable.
- Canonical hash `#roster/progress`; legacy `#roster/attributes` and `#roster/*/attributes` still open Progress. Refresh round-trips.
- Verified: `npx vitest run tests/squad-route.test.ts tests/ha-history-store.test.ts tests/squad-ha-table.test.ts` (57 passed); `npx tsc --noEmit`. Suggest untouched.
