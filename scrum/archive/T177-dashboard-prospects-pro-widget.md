---
id: T177
title: Dashboard prospects with Pro mentor room
status: done
priority: 3
owner: cursor-agent
claimed_at: 2026-08-27T01:42:00Z
started_at: 2026-08-27T01:42:00Z
completed_at: 2026-08-27T01:45:00Z
depends_on: [T176]
---

# T177 — Dashboard prospects with Pro mentor room

## Why

Loop A/B: surface young high-ceiling players who can still gain Professionalism from someone already on the squad — one click into the desk, no mentoring product chrome.

## Scope

- In: Dashboard highlight of managed-squad prospects using dynamic rules (age + PA ≥ squad median CA + mentor with Pro ≥ subject Pro + 2); click opens player; empty copy when none; domain helper + unit test; reuse dashboard card pattern
- Out: Full mentoring desk / role nav; fixed wonderkid lists; Tactic/HoYD chrome; movers (T176)

## Acceptance criteria

- [x] Dashboard shows a Prospects (or equivalent) panel when rules match
- [x] Young filter: age ≤ 21, or youngest third of squad (cap ~23) if that yields too few with known age
- [x] High pot: known PA ≥ squad median of known CA
- [x] Pro room: subject has readable Pro; at least one other squad player with Pro ≥ subject Pro + 2
- [x] Rank by Pro gap then PA−median CA; cap ~5–8; click opens player
- [x] Empty state when no matches; domain logic unit-tested

## Notes / pointers

- Live fields: `age`, `currentAbility`, `potentialAbility`, `personalityAttributes.Professionalism`
- Mentoring reads: `desktop/src/domain/mentoring-match.ts`
- UI after T176: `desktop/src/components/dashboard-screen.tsx`

## Progress

Shipped: `rankSquadProspects` + tests; Dashboard Prospects panel (PA + Pro → best mentor). Verified with vitest (5 prospects + 6 movers).

Commit: _(pending)_
