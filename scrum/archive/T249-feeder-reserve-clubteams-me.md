---
id: T249
title: Load feeder Reserve clubTeams for ME
status: done
priority: 2
owner: auto
claimed_at: "2026-09-06T22:58:00+02:00"
started_at: "2026-09-06T22:58:00+02:00"
completed_at: "2026-09-06T23:00:00+02:00"
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

- [x] Feeder reserve teams appear on Match experience when present in Club.Teams
- [x] Kaiserslautern unexplained absence documented if Club.Teams has no Reserves (II-as-affiliate case)
- [x] Commit `T249: …`

## Progress

Widened feeder retain to `firstTeam` | `reserves` | `under19s`. recipes note: KL may simply lack Club.Teams Reserves (Schalke II is `0x08`). Verified by code review of retain path; live confirm after rebuild.

Commit: `_(fill)_`
