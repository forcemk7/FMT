---
id: T204
title: Squad — status filters + rosterLen in Settings
status: done
priority: 3
owner: auto
claimed_at: "2026-09-04T05:08:00+02:00"
started_at: "2026-09-04T05:08:00+02:00"
completed_at: "2026-09-04T05:12:00+02:00"
depends_on: []
---

# T204 — Squad — status filters + rosterLen in Settings

## Why

Squad team tabs currently dump opaque counts in the label: `{name} ({rosterLen}; {atClub}, {loanedIn}, {loanedOut})`. Those numbers only help if they drive a filter. Loop A needs to see who’s at club vs loaned in/out on the selected team without decoding paren noise.

## Scope

- In: Strip status/roster counts from squad team **tab labels** (name only for now — in-game Club.Teams string polish is a later thread)
- In: Same toolbar row as team tabs: **right-aligned** status filters for **At club / On loan (loaned in) / Loaned out**, each showing the count for the **selected** team (`countSquadTeamRoster`)
- In: Filtering applies to the Squad desk matrix for the active team tab (multi-select; default = all three on so list parity with today)
- In: Surface each club team’s FM `rosterLen` as a **dev readout in Settings** (not on the Squad tabs)
- Out: Renaming tabs to richer in-game Club.Teams labels
- Out: Changing Loans / GM / HoYD desks; affiliate / separate-club RE
- Out: New extract / RE — reuse existing `squadRosterStatus` / `countSquadTeamRoster` / player flags

## Acceptance criteria

- [x] Squad team tabs show display name only (no `(roster; a, b, c)` suffix)
- [x] Toolbar has right-aligned At club / On loan / Loaned out filters with live counts for the selected team
- [x] Toggling filters changes which players appear in the selected team’s matrix; empty filter set → empty matrix (or clear empty hint)
- [x] Settings shows club-team `rosterLen` values when a live snapshot is connected (dev diagnostic)
- [x] Domain helpers stay the source of truth; unit coverage for filter/count labeling if labels move
- [x] One commit `T204: …`

## Notes / pointers

- UI today: `desktop/src/components/my-team-screen.tsx` toolbar + `squadTeamTabLabel`
- Counts: `countSquadTeamRoster` / `squadRosterStatus` in `desktop/src/domain/live-data.ts`
- Terminology: tab “on loan” = **loanedIn** (arrivals); **loanedOut** = outgoing (also has Loans nav twin — do not collapse desks)
- Prefer compact checkboxes (or equivalent toggles) over a nested dropdown so counts stay visible
- Prefer: do not invent new status enums — map UI labels onto existing `SquadRosterStatus`

## Progress

Shipped:
- `squadTeamTabLabel` → name only; filters on Squad toolbar (At club / On loan / Loaned out) with selected-team counts
- `playerMatchesSquadRosterFilters` + tests; default all three enabled
- Settings expand: Club team roster lengths (`rosterLen`) when connected

Verify: `npm test -- --run src/domain/live-data.test.ts` — 32 passed.

Commit: `9f702ceb07df5a1593bd520c15f02b77fea4a341`
