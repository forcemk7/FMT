---
id: T189
title: Loans desk = outgoing loanedOut players
status: done
priority: 1
owner: cursor-worker
claimed_at: "2026-08-27T21:38:00+02:00"
started_at: "2026-08-27T21:38:00+02:00"
completed_at: "2026-08-27T21:41:22+02:00"
depends_on: [T182]
---

# T189 — Loans desk = outgoing loanedOut players

## Why

T182 hid outgoing loans from Squad. Honesty needs a place to see them: short list to check against FM Overview → Loans. Same desk shape as Squad so the owner already knows how to read it.

## Scope

- In: Live **Loan Manager** nav (no longer Later stub)
- In: Desk = Squad card/matrix structure filtered to managed-club `loanedOut` players
- In: Open player → existing profile desk
- In: Empty state when connected and zero outgoing loans
- Out: Loan club name/wage/fee columns, sell flow, inbound loans, recommendations, unit FT/II/U19 sections

## Acceptance criteria

- [x] Loan Manager nav is live (not roadmap stub)
- [x] Loans desk lists only players with `loanedOut` for the managed club
- [x] Same positional grouping / CA·PA·HAS cards as Squad
- [x] Click opens player profile; Squad still excludes those players

## Notes / pointers

- `isLoanedOutSquadPlayer` + `MyTeamScreen mode="loaned-out"`
- Nav: `shell-header` Loans `live: true`; `fmt-app` routes Loan Manager to desk

## Progress

### Shipped

1. `isLoanedOutSquadPlayer` + tests
2. `MyTeamScreen` mode `at-club` | `loaned-out` (shared cards/matrix)
3. Loan Manager live in shell; Later stub removed for Loans only

### Verified

- `vitest` `live-data.test.ts` (3 tests)
- Logic: inverse of T182 filter on same snapshot players

### Commit

_(filled after git)_
