---
id: T176
title: Dashboard movers since last load
status: done
priority: 2
owner: cursor-agent
claimed_at: 2026-08-27T01:34:00Z
started_at: 2026-08-27T01:34:00Z
completed_at: 2026-08-27T01:40:00Z
depends_on: []
---

# T176 — Dashboard movers since last load

## Why

Loop B: Dashboard should surface who changed since the last history change-point so the user jumps straight into the player desk without hunting Squad.

## Scope

- In: Dashboard panel listing managed-squad players with any non-zero recent attr/history delta; click opens player; empty state when no second point or no moves; domain helper + light unit test; reuse HAS-card visual pattern
- Out: Prospects/mentoring widget (T177); favorites strip; new RE; mentoring desk

## Acceptance criteria

- [x] Connected squad Dashboard shows a “Movers” (or equivalent) panel of players with recent history deltas
- [x] Each row/card opens that player’s profile
- [x] Empty when only one history point or nothing changed
- [x] Domain ranking/filter is unit-tested

## Notes / pointers

- History: `desktop/src/domain/attribute-history.ts` (`recentDeltasForPlayer`, store appends on load)
- UI: `desktop/src/components/dashboard-screen.tsx` (HAS Top/Bottom pattern)
- Managed squad only (`clubId === managedClubId`)

## Progress

Shipped: `rankSquadMovers` + unit tests; Dashboard Movers panel (chips for changed fields, click → profile). Verified with `vitest run src/domain/attribute-history.test.ts` (6 pass).

Commit: `6acb0bd`
