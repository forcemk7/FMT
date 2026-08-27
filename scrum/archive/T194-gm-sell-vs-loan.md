---
id: T194
title: GM advises Sell vs Loan from squad avg CA
status: done
priority: 2
owner: cursor-worker
claimed_at: "2026-08-27T23:13:00+02:00"
started_at: "2026-08-27T23:13:00+02:00"
completed_at: "2026-08-27T23:15:42+02:00"
depends_on: [T192]
---

# T194 — GM advises Sell vs Loan from squad avg CA

## Why

T192 used fixed PA≤140 + headroom. Owner’s real rule is relative to **this club’s squad average CA**, and GM must split advice: **Sell** vs **Loan** (not one undifferentiated move-on pile).

## Law (v1)

Let `avgCA` = mean `currentAbility` of **at-club** managed-squad players with finite CA (same population as Squad desk).

| Advice | Predicate |
|--------|-----------|
| **Sell** | finite CA+PA; `PA < avgCA`; `PA − CA ≤ HEADROOM_MAX` (keep **8**) |
| **Loan** | finite CA+PA; `PA ≥ avgCA`; `CA < avgCA` |

A player matches at most one lane. Missing CA/PA → excluded. Drop `PA_MOVE_ON_MAX`.

## Scope

- In: Domain helpers — `squadAverageCA`, `gmAdvice(player, avgCA) → "sell" | "loan" | null`
- In: GM desk shows **two** labeled groups (Sell / Loan), same cards as Squad within each; empty copy per group when zero
- In: Heading blurb can show `avgCA` (rounded) so the owner trusts the split
- Out: Settings knobs, transfer/loan workflows, world search, changing Loans desk, mentoring

## Acceptance criteria

- [x] Sell list = only at-club players with PA below squad avg CA and CA≈PA (headroom ≤ 8)
- [x] Loan list = only at-club players with PA ≥ avg CA and CA < avg CA
- [x] Fixed `PA_MOVE_ON_MAX` no longer drives GM
- [x] Unit tests for avgCA + both advice lanes (include / exclude / neither)

## Notes / pointers

- Steal T192 `mode="move-on"` / `MyTeamScreen`; replace `isMoveOnCandidate` with advice lanes
- `HEADROOM_MAX` stays named constant = 8

## Progress

### Shipped

1. `squadAverageCA` + `gmAdvice` (`sell` | `loan` | null); dropped `PA_MOVE_ON_MAX` / `isMoveOnCandidate`
2. GM desk: Sell / Loan lanes with position cards; heading shows avg CA + counts
3. SCOPE already locked club-relative Sell/Loan law

### Verified

- `vitest` `live-data.test.ts` (8 tests)

### Commit

`4a4b2514df261095a4d045b879155fcc8a674745` (domain + board). UI lanes landed earlier in `f76e7e6` with T193.
