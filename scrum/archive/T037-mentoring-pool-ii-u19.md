---
id: T037
title: Mentoring pool includes II and U19 (not FT-only)
status: done
priority: 1
owner: auto
claimed_at: 2026-08-13T16:55:00Z
started_at: 2026-08-13T16:55:00Z
completed_at: 2026-08-13T17:00:00Z
depends_on: [T036]
---

# T037 — Club-wide mentoring eligibility

## Why

Personalities table is club-wide. Checkboxes / Add mentoring unit still only work for **FT** because Mentoring cache is built from `firstTeamMentoringPlayers()`. U19/II kids and seniors cannot be stored as units — loop break for the stated flow.

## Scope

- In: Mentoring candidate pool = at-club **FT + Reserves + U19** (same loaned-out ban). Wire `ensureMentoringCacheForRoster` / prune trust / incomplete counts to that pool — not FT-only
- In: HA table checkboxes appear for eligible II/U19 rows; Add mentoring unit can mix units (e.g. FT senior + U19 mentee)
- In: Mentoring tab lists those groups the same way
- Out: Suggest; CA/PA columns; Loans in mentoring; changing FM in-game groups

## Acceptance criteria

- [x] U19 / II at-club players show a checkbox (when unassigned) on Personalities
- [x] Add mentoring unit with mixed FT+U19 (or II) succeeds and persists
- [x] Mentoring tab shows the same group
- [x] Loaned-out still excluded
- [x] No Suggest

## Notes / pointers

- `firstTeamMentoringPlayers()` in `web/main.ts` — replace call sites for pool with club-at-club helper (dedupe uid)
- `squadHaMentoringEligibleUids` → follows Mentoring cache
- Keep prune min-headcount honest for the larger pool

## Progress

Shipped `clubAtClubMentoringPlayers()` (FT+II+U19, loaned-out out, uid dedupe). Replaced all Mentoring pool call sites (cache, session key, incomplete young, prune trust, picker, empty copy). Bumped `MENTORING_LOGIC_REV` to 15. Verified: `tsc --noEmit`, `vitest run tests/mentoring-stack.test.ts`.
