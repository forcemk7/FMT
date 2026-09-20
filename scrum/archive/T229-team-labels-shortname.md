---
id: T229
title: TeamType Under Ns; affiliate shortName; profile team shortName
status: done
priority: 3
owner: cursor-agent
claimed_at: "2026-09-06T03:44:00+02:00"
started_at: "2026-09-06T03:44:00+02:00"
completed_at: "2026-09-06T03:54:00+02:00"
depends_on: []
---

# T229 â€” TeamType Under Ns; affiliate shortName; profile team shortName

## Why

Managed club tabs should stay simple TeamType labels (`First Team`, `Under 19s`). Affiliate tabs need team shortName (`Schalke 04 II`). Player profile Club fact should show the player's team shortName (`Schalke 04` / `Schalke 04 U19` / `Schalke 04 II`), not always the parent club full name.

## Scope

**In:**

- TeamType U labels â†’ `Under {n}s` (TS + Rust)
- Managed club teams (no affiliationType): TeamType labels
- Affiliated teams: prefer `shortName` (team+0x20), else name / map reminder
- Expose `LiveClubTeam.shortName` from load
- Profile Club fact: resolve `squadTeamUid` â†’ team shortName (fallback name / club name)

**Out:** Club-level nickname RE; renaming route IDs; First XI

## Acceptance criteria

- [x] Managed tabs: First Team / Under 19s / â€¦ (not U19)
- [x] Affiliate tab uses shortName when present
- [x] Profile Club shows team shortName for FT / U19 / II cases
- [x] Tests + one commit `T229: â€¦`

## Progress

Confirmed before ship: profile used club full name only; shortName was validated in entity-map but not on LiveClubTeam / tabs.

Shipped: Under Ns TeamType; shortName on load JSON; affiliate tabs prefer shortName; `playerTeamDisplayName` on profile; recipes note. Vitest 41 + cargo team_type/resolve_team_tab_label ok.

Commit `69c167c`.


