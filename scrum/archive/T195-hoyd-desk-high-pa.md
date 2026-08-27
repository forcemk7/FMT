---
id: T195
title: HoYD desk = Squad twin filtered to high-PA groom list
status: done
priority: 2
owner: cursor-agent
claimed_at: "2026-08-28T01:07:00+02:00"
started_at: "2026-08-28T01:07:00+02:00"
completed_at: "2026-08-28T01:11:00+02:00"
depends_on: [T194]
---

# T195 — HoYD desk = Squad twin filtered to high-PA groom list

## Why

Owner grooms youth from Squad by scanning PA. HoYD is that filtered queue: at-club players with **high PA vs squad median CA**, sorted PA desc — same Squad cards, one click to profile desk.

## Scope

- In: Live **HoYD** nav (no longer Later stub)
- In: Desk = Squad card/matrix filtered to at-club **groom prospects** (`PA ≥ squad median CA`, headroom > 8)
- In: Sort within position groups by PA desc (not CA)
- In: Domain predicate `isHoydProspect` beside GM helpers
- In: Empty state when connected and zero matches
- Out: Settings knobs, mentoring matcher, age gates, world search, unit FT sections

## Acceptance criteria

- [x] HoYD nav is live (not roadmap stub)
- [x] HoYD desk lists only at-club players matching groom predicate
- [x] Same positional grouping / CA·PA·HAS cards as Squad; sorted by PA
- [x] Click opens player profile; Squad / Loans / GM unchanged
- [x] Predicate unit-tested (include / exclude)

## Progress

### Shipped

1. `isHoydProspect` — `PA ≥ squad median CA` and headroom > `MOVE_ON_HEADROOM_MAX` (8)
2. `MyTeamScreen` mode `hoyd`; position groups sorted by PA desc
3. HoYD nav live; route off `LaterRoleScreen`
4. SCOPE Loop C HoYD definition locked

### Verified

- `vitest` `live-data.test.ts` (15 tests)

### Commit

_(pending)_
