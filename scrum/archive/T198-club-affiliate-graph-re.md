---
id: T198
title: RE — club affiliate graph (live RAM probe)
status: done
priority: 1
owner: auto
claimed_at: 2026-08-30T14:00:00Z
started_at: 2026-08-30T14:00:00Z
completed_at: 2026-08-30T14:05:00Z
depends_on: []
---

# T198 — RE — club affiliate graph (live RAM probe)

## Why

German reserves (Schalke II) are a **separate club entity**, not a team under club UID 920. Youth locked via same-club team objects. Reserves need `managed club → affiliate clubs (typed) → team → roster`. Legia/Kaiserslautern are affiliates too but not reserve squads — must discriminate by relationship type, not Schalke-only heuristics.

## Scope

- In: `debug_scan_club_affiliates` — forward/back club pointer links from managed club object + affiliate club teams/rosters in dump
- In: relationship-type **candidates** (nearby u32) documented for human/FM UI compare
- Out: loading reserve rosters (T199); hardcoding Schalke UID 13217; `.fm` extract

## Acceptance criteria

- [x] Tauri command registered; returns JSON with managed club + linked clubs (UID, name, pointer offsets)
- [x] Distinguishes same-club reserve teams vs separate-club affiliates in output sections
- [x] Unit test for link-scan helper (synthetic bytes, no FM)
- [x] Progress documents how to compare dump vs FM Board → Affiliated Clubs
- [x] One commit `T198: …`

## Progress

Shipped `debug_scan_club_affiliates` + `fm26/club_affiliates.rs`:
- **forwardLinksFromManagedClub** — club pointers embedded in managed club object (8KB probe)
- **backLinksToManagedClub** — heap club objects whose blob points at managed club (Schalke II / feeder candidates) + teams/rosterLen
- **sameClubReserveTeams** — existing same-club `discover_managed_club_teams` rows classified `reserves`
- **relationshipCandidates** — nearby u32 at each link offset for FM “Affiliated Clubs” type RE

**Human verify (Schalke save, FM open):**
1. DevTools / invoke `debug_scan_club_affiliates`
2. Board → Affiliated Clubs: note each name + relationship label (B Team vs Feeder etc.)
3. Match `backLinksToManagedClub` / `forwardLinksFromManagedClub` names to FM list
4. Note which `relationshipCandidates.u32` is stable per type → T199 filter input

Tests: `cargo test club_affiliates --lib` (2/2). Live probe not run in CI.

Commit: bf0af49dbd79d04742429028f39fe86d095cdbb2
