---
id: T251
title: Load feeder II Club (affiliate-of-affiliate) for ME
status: done
priority: 1
owner: auto
claimed_at: "2026-09-06T23:03:00+02:00"
started_at: "2026-09-06T23:03:00+02:00"
completed_at: "2026-09-06T23:10:00+02:00"
depends_on: [T249]
---

# T251 — Load feeder II Club (affiliate-of-affiliate) for ME

## Why

Kaiserslautern II is a separate II Club under KL (same shape as Schalke → Schalke II), not a TeamType on KL. Loan ladder needs that rung; Legia/Sparta already expose same-club Reserves/B/II via Club.Teams.

## Scope

- In: After loan-on feeders resolve, walk each feeder `club+0x118` for type `0x08` II Club; load First Team roster
- In: Mark second-hop II as Match-experience-only (Squad desk must not gain new tabs)
- In: Stamp player clubId to the II club (not managed) so HoYD/GM don’t treat them as employees
- Out: Recursive feeder-of-feeder Normal/0x03; T250 strength chrome

## Acceptance criteria

- [x] Kaiserslautern II (or equivalent feeder II) appears on Match experience when present
- [x] Squad desk still only shows managed + direct Schalke II (no KL II tab)
- [x] recipes.md notes one-hop feeder→II walk
- [x] Commit `T251: …`

## Progress

One-hop walk from loan-on feeders for `0x08`; `matchExperienceOnly` on clubTeams; Squad filters it; roster stamp uses II club uid. `cargo check` ok.

Commit: `_(fill)_`
