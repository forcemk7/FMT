---
id: T234
title: Profile stop clubName substitute; shortName map honesty
status: done
priority: 3
owner: cursor-agent
claimed_at: "2026-09-06T05:05:00+02:00"
started_at: "2026-09-06T05:05:00+02:00"
completed_at: "2026-09-06T05:08:00+02:00"
depends_on: [T233]
---

# T234 — Profile stop clubName substitute; shortName map honesty

## Why

U19 profiles show real `shortName` (`Schalke 04 U19`). FT/II show `FC Schalke 04` because the profile UI still falls back to `parentClubName` when short is empty — that is a lie vs the pure shortName rule. Entity-map shortName was only validated for U19 `team+0x20`, not FT/II.

## Scope

**In:**

- Profile Club fact uses `playerTeamDisplayName` only (shortName); no `parentClubName` / `club.name` substitute
- Entity-map / recipes: note shortName validated for U19; FT often has empty team name fields (club fallback for full name)
- Load already logs `short=` per team

**Out:** Inventing short from full name; claiming club shortName offset without RE

## Acceptance criteria

- [x] FT/II profile with empty shortName shows — (not `FC Schalke 04`)
- [x] U19 profile still shows shortName when present
- [x] Map/recipes honesty; one commit `T234: …`

## Progress

Removed profile `parentClubName` / `club.name` substitute. Documented that team+0x20 shortName is proven for U19 only; FT/II empty short is a map gap (club shortName unmapped), not “shortName isn’t real”.

Commit SHA after commit.
