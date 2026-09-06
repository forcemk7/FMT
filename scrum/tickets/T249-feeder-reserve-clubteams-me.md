---
id: T249
title: Load feeder Reserve clubTeams for ME
status: ready
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T245]
---

# T249 — Load feeder Reserve clubTeams for ME

## Why

Legia / Sparta Praha (and similar) feeders should show Reserve alongside First + Under N. Today feeders only keep `firstTeam` | `under19s` in `load_bteam_affiliate_rosters` — Reserves are dropped on purpose, not missing from FM.

## Scope

- In: Feeder Club.Teams retain Reserves (`squad_unit` reserves / TeamType Reserves) with roster > 0, same as First + Under N
- In: ME sort already bands Reserves between First and Under N (T248)
- Out: Loan-byte (T245); strength/visual polish (T250); Squad desk tabs for feeder reserves

## Acceptance criteria

- [ ] Feeder reserve teams appear on Match experience when present in Club.Teams
- [ ] Kaiserslautern unexplained absence documented if Club.Teams has no Reserves (II-as-affiliate case)
- [ ] Commit `T249: …`

## Progress

Ready after T245. Root cause already known: explicit retain filter.
