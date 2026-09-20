---
id: T241
title: Roster-load AffiliationType 0x03 feeders
status: done
priority: 1
owner: auto
claimed_at: "2026-09-06T20:49:00+02:00"
started_at: "2026-09-06T20:49:00+02:00"
completed_at: "2026-09-06T20:52:00+02:00"
depends_on: []
---

# T241 — Roster-load AffiliationType 0x03 feeders

## Why

Schalke warnings: `Map AffiliationType 0x03`, `7/12` mapped, only 1 II club resolved. Feeders for Match experience are `0x03`, not `0x01`.

## Scope

- In: Add `0x03` to roster-load allow-list; load Club.Teams like Normal (`0x01`); keep off Squad desk; ME sort treats `0x03` as feeder band; update recipes
- Out: Inventing a PGE display name for `0x03` (keep Map reminder until labeled)

## Acceptance criteria

- [x] `is_roster_load_affiliation_type` includes `0x03`
- [x] Squad desk hides `0x01` and `0x03`
- [x] Match experience feeder band includes `0x03`
- [x] recipes.md documents `0x03` roster-load
- [x] Tests + commit `T241: …`

## Progress

- Allow-list `0x01|0x03|0x08`; feeder load path shared; Squad filters both feeders
- Fixed ME band so non-`0x01` affiliates are not all treated as II
- recipes: Schalke `0x03` evidence
- vitest match-experience 9/9

Commit: `e1b8712`