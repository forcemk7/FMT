---
id: T236
title: Match experience profile tab (same-pos CA by clubTeam)
status: done
priority: 2
owner: auto
claimed_at: "2026-09-06T18:57:00+02:00"
started_at: "2026-09-06T18:57:00+02:00"
completed_at: "2026-09-06T19:02:00+02:00"
depends_on: []
---

# T236 — Match experience profile tab (same-pos CA by clubTeam)

## Why

Answer “which team should this player be in?” on the player desk: compare this player’s CA to same-primary-position competition on each already-loaded clubTeam (FMLE glance, no new RE).

## Scope

- In: Profile tab **Match experience**; one card per loaded `clubTeams` entry; filter to focus player’s best primary position; rank by CA; highlight focus player (inject if not on that roster)
- In: Pure domain helper + unit test; reuse existing squad team labels / sort
- Out: Loading extra Normal-affiliate feeders; logos polish; auto move/stay suggestion; playing-time / tactical need RE

## Acceptance criteria

- [x] Profile has Match experience tab next to Attributes / Development
- [x] Each loaded clubTeam shows a same-position CA-ranked list with the focus player marked
- [x] Empty / no-position state is honest (no fake ranks)
- [x] Domain helper covered by unit test
- [x] One commit `T236: …`

## Notes / pointers

- `player.bestCalculatedPosition` / `positions`; roster via `squadTeamUid`
- `sortClubTeamsForSquadDesk`, `squadTeamDisplayName`
- No affiliate discovery expand in this ticket

## Progress

Shipped profile **Match experience** tab:
- Domain `buildMatchExperienceCards` / `matchExperiencePosition` — per loaded clubTeam, primary-position peers sorted by CA; focus always included (`projected` when not on that roster, `current` when on it)
- UI cards with optional primary position switcher; click peers to open profile
- Verified: `vitest run src/domain/match-experience.test.ts` (4/4)

Commit: _(filled after git)_
