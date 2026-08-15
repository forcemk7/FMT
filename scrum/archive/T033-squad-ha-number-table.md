---
id: T033
title: Squad HAS-style table + one-click not-worse-than preset
status: done
priority: 1
owner: Auto
claimed_at: 2026-08-13T15:06:00Z
started_at: 2026-08-13T15:10:00Z
completed_at: 2026-08-13T15:26:00Z
depends_on: []
---

# T033 — Squad is the HAS table; click kid = ≥ floors from save

## Why

**Loop:** click the player you want to mentor (or two) → see if anyone in the squad would **only grow** their personality HA.

One-click is not a new mode. It is a **preset** that writes the same customizable column filters as the HAS ranker, using **this save’s actual numbers** as floors. User can then loosen/drop any filter.

## Scope

- In: Squad Personalities = **HAS ranker table** pointed at extract: Name, Personality, Media, DET PRO PRE AMB TEM LEA LOY SPO CON, optional HAS. Sortable. Steal ranker look. No Mid/Band. Missing = `—`. Never inferred mids as exact
- In: **Customizable filters** like the ranker (per-attr op + value). User can add/edit/clear
- In: **One-click preset:** select 1 player, or 2 (pair). Applies template **≥ all growth HA / ≤ CON** with thresholds from the selection:
  - DET, PRO, PRE, AMB, TEM, LEA, LOY, SPO: floor = **max** of selected players’ extract values
  - CON: ceiling = **min** of selected (lower is better)
  - Writes those into the normal filter rows (not a parallel magic path)
  - Click/select is the main gesture (row click or equivalent). Selected rows stay visible
  - Candidate with a missing attr vs a required floor: hidden (fail closed)
- Out: Suggest; seating; auto-pick “best mentor”; Dynamics; T014; Talent; full tech/physical cards; HAS score as the better-than test; new pages

## Acceptance criteria

- [x] Table compares two players’ Pro/Det/Amb with no hover
- [x] Click kid K: filters become DET≥K.det, PRO≥K.pro, … CON≤K.con from **this save**. Table shows only K plus players not worse on that vector
- [x] Click two players: floors are per-attr max (CON min). A mentor must not pull either down
- [x] After one-click, user can change or delete a single filter (e.g. drop SPO) without resetting the rest
- [x] Senior with lower Pro than the floor disappears; equal can remain if nothing else is worse
- [x] Incomplete extract cannot look complete
- [x] No Suggest changes

## Notes / pointers

- Steal filter UI from ranker (`rankerFilters`, `#ranker-filter-rows`) — reuse, don’t fork a second language
- Data: roster `PersonalitySignals` / pack + Det/Lea
- Pane: `#squad-personalities-pane` / `#roster-body`
- SCOPE.md

## Progress

Shipped Squad Personalities as a ranker-style number table on the Career Save extract (Name, Personality, Media, DET PRO PRE AMB TEM LEA LOY SPO CON, HAS). Missing cells are `—`. No Mid/Band. Row click selects 1 or 2 players and writes the normal per-attr filters (≥ max, CON ≤ min) from this save; selected rows stay visible; missing required attrs fail closed. Filters remain editable/deletable after the preset. HAS is display-only, not the better-than test. Suggest/seating/T001/T003/T014 untouched.

Verified: `npx vitest run tests/squad-ha-table.test.ts` (12 passed); `npx tsc --noEmit`.
