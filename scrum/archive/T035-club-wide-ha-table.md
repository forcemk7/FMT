---
id: T035
title: Merge FT / Reserves / U19 into one HA table with unit column
status: done
priority: 1
owner: worker
claimed_at: "2026-08-13T16:06:00Z"
started_at: "2026-08-13T16:07:00Z"
completed_at: "2026-08-13T16:15:00Z"
depends_on: [T033]
---

# T035 — Club-wide personality HA list

## Why

Mentors are not only in the kid’s unit. Switching First Team / Reserves / Under 19s to run the same ≥ filter is the wrong drill. One list, with **which squad** visible.

## Scope

- In: Personalities HA table = **at-club** First Team + Reserves + Under 19s in one list (still exclude loaned-out)
- In: **Unit** column (or equivalent glance label): FT / II / U19 — sortable/filterable if cheap; at least always visible
- In: Same one-click ≥ preset and Clear behavior across the merged list
- In: Collapse or remove the three unit tabs as the Personalities navigator — keep **Loans** and **Mentoring** tabs as they are
- Out: Suggest; Loans merge; Mentoring rewrite; T014; new product

## Acceptance criteria

- [x] After load, one table shows FT + II + U19 at-club players without switching tabs
- [x] User can tell each row’s unit at a glance (column or badge)
- [x] Click a U19 kid; FT seniors who pass ≥ floors appear in the same filtered view
- [x] Loaned-out still excluded; Loans / Mentoring tabs unchanged in purpose
- [x] No Suggest changes

## Notes / pointers

- `firstTeamPlayers` / `reservesPlayers` / `under19sPlayers` already exist; mentoring already concatenates them
- `web/main.ts` `activeSquadPlayers` / `renderRoster` / T033 table
- Dedupe by `uid` if a player appears in more than one extract list

## Progress

Shipped club-wide Personalities HA: `mergeClubWideAtClubPlayers` (FT→II→U19, uid dedupe, loaned-out out) feeds the T033 table with a Unit column (FT / II / U19). Navigator is Personalities | Loans | Mentoring (unit tabs hidden). One-click ≥ preset unchanged across the merged list. Legacy `#roster/reserves` / `#roster/under19s` hashes land on club-wide Personalities.

Verified: `npx vitest run tests/squad-ha-table.test.ts` (16 passed); `npx tsc --noEmit`. Suggest / T014 untouched.
