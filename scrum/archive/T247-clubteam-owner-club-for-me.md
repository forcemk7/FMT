---
id: T247
title: clubTeam owner clubId/name for ME headers
status: done
priority: 1
owner: auto
claimed_at: "2026-09-06T22:04:00+02:00"
started_at: "2026-09-06T22:04:00+02:00"
completed_at: "2026-09-06T22:11:00+02:00"
depends_on: [T246]
---

# T247 — clubTeam owner clubId/name for ME headers

## Why

II card shows “FC Schalke 04” because ME resolves name via player `clubId` (stamped managed for Squad). Real II name is known at affiliate load (`affiliate.club_name`) but not on `LiveClubTeam`.

## Scope

- In: Stamp `clubId` + club display name on each discovered `clubTeam` (managed / II / feeder) from the owning club
- In: ME header logo + clubName prefer `team.clubId` / owner name over roster player clubId
- Out: Changing player `clubId` for Squad/HoYD; loan-byte filter (T245)

## Acceptance criteria

- [x] II ME card shows II club name (e.g. FC Schalke 04 II), not parent
- [x] Feeder cards unchanged / still correct
- [x] Player clubId stamping for II stays managed
- [x] Tests + commit `T247: …`

## Progress

Shipped: `DiscoveredClubTeam.club_id` / `club_name` from managed or `affiliate`; JSON `clubId`/`clubName` on clubTeams; ME prefers team owner over player stamp. Player roster clubId for II unchanged. Verified vitest (11) + `cargo check`.

Commit: `_(fill)_`
