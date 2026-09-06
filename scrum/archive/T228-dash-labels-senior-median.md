---
id: T228
title: Dash widget labels + senior-team median for HoYD/GM
status: done
priority: 3
owner: cursor-agent
claimed_at: "2026-09-06T03:22:00+02:00"
started_at: "2026-09-06T03:22:00+02:00"
completed_at: "2026-09-06T03:24:00+02:00"
depends_on: []
---

# T228 — Dash widget labels + senior-team median for HoYD/GM

## Why

Dashboard widget names should match the decision language. HoYD/GM median CA was club-wide (youth/reserves dilute it); ref must be senior/manager team so pipeline advice toward First Team is meaningful.

## Scope

**In:**

- Dash titles: Movers→Development, Prospects→Best talent, HAS Top→Top personalities, HAS Bottom→Worst personalities (IDs may stay for routing)
- HoYD/GM `refCA` = median CA of senior (`isManagerTeam`) at-club roster; candidate pool stays club-wide at-club employees
- Vitest for senior median helper if added

**Out:** First XI RE; affiliate median; renaming Screen route IDs unless needed

## Acceptance criteria

- [x] Dashboard peeks + full views show the new titles
- [x] HoYD/GM median uses senior team only; suggestions still from club-wide at-club pool
- [x] One commit `T228: …`

## Progress

Shipped: dashViewTitle labels; `seniorAtClubPlayers` + median for HoYD/GM; SCOPE wording; live-data tests. Commit SHA after commit.
