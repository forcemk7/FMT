---
id: T192
title: GM desk = Squad twin filtered to move-on
status: done
priority: 2
owner: cursor-worker
claimed_at: "2026-08-27T22:33:00+02:00"
started_at: "2026-08-27T22:33:00+02:00"
completed_at: "2026-08-27T22:35:28+02:00"
depends_on: [T189]
---

# T192 — GM desk = Squad twin filtered to move-on

## Why

Owner already runs move-on decisions in Squad: promote who belongs, then find players whose **PA is too low** to become meaningful contributors and **CA≈PA** (little headroom → first-team minutes won’t inflate value). GM is that filtered queue so the scan isn’t repeated on the full roster. Exit is always leave: sell now, or loan to bump value then sell.

## Scope

- In: Live **General Manager** nav (no longer Later stub)
- In: Desk = Squad card/matrix structure filtered to **at-club** move-on candidates
- In: One domain predicate `isMoveOnCandidate` (or equivalent) with **named constants** at file top:
  - headroom: `PA - CA ≤ HEADROOM_MAX` (v1 default **8**)
  - ceiling: `PA ≤ PA_MOVE_ON_MAX` (v1 default **140**)
  - both CA and PA must be known finite numbers
- In: Open player → existing profile desk
- In: Empty state when connected and zero move-on matches
- Out: Settings knobs, club-relative auto-calibration, sell/loan UI, recommendations, inbound deals, world search, unit FT/II/U19 sections, changing Loans behavior

## Acceptance criteria

- [x] General Manager nav is live (not roadmap stub)
- [x] GM desk lists only at-club players matching the move-on predicate (low PA + CA≈PA)
- [x] Same positional grouping / CA·PA·HAS cards as Squad
- [x] Click opens player profile; Squad / Loans filters unchanged
- [x] Predicate + constants unit-tested (include / exclude cases)

## Notes / pointers

- Steal T189: `MyTeamScreen` mode + `shell-header` `live: true` + `fmt-app` route off `LaterRoleScreen`
- Filter layer: `live-data.ts` beside `isAtClubSquadPlayer` / `isLoanedOutSquadPlayer`
- Not blocked on T190 (pack-history deltas are unrelated)

## Progress

### Shipped

1. `isMoveOnCandidate` + `MOVE_ON_HEADROOM_MAX=8` / `PA_MOVE_ON_MAX=140`
2. `MyTeamScreen` mode `move-on` (at-club ∩ predicate); empty connected state
3. GM nav live; Later stub removed for General Manager only
4. SCOPE Loop C GM definition locked

### Verified

- `vitest` `live-data.test.ts` (5 tests)

### Commit

_(filled after git)_
