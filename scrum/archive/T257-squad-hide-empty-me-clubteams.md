---
id: T257
title: Squad desk — hide empty / ME-only clubTeams
status: done
priority: 1
owner: auto
claimed_at: "2026-09-07T00:18:00+02:00"
started_at: "2026-09-07T00:18:00+02:00"
completed_at: "2026-09-07T00:21:00+02:00"
depends_on: []
---

# T257 — Squad desk — hide empty / ME-only clubTeams

## Why

Empty clubTeam tabs (e.g. Youth(0)) returned on Squad. App law: Squad = managed First / U19 / II with loaded players. Feeders + empty shells stay off.

## Scope

- In: `isSquadDeskClubTeam` — exclude ME feeders / matchExperienceOnly; exclude zero **loaded** players; keep manager
- In: Feeder affiliate clubTeams stamped `matchExperienceOnly` at load
- Out: Deleting Youth from FM discovery; ME/loan rule changes

## Acceptance

- [x] Squad tabs with loaded count 0 do not appear (except manager First)
- [x] Feeder / ME-only teams still absent from Squad
- [x] Commit `T257: …`

## Progress

- Shipped: `isSquadDeskClubTeam` + feeder `matchExperienceOnly`; recipes note
- Verified: vitest live-data (42)
- Commit: (this ticket)
