---
id: T191
title: Loans age + loan club honesty
status: done
priority: 1
owner: cursor-worker
claimed_at: "2026-08-27T21:49:00+02:00"
started_at: "2026-08-27T21:49:00+02:00"
completed_at: "2026-08-27T21:58:26+02:00"
depends_on: [T189]
---

# T191 — Loans age + loan club honesty

## Why

Loans desk cards show `—` for age (DOB present, game date often missing on loaned player objects). Owner also needs Loan Club visible so the list matches FMLE Parent/Loan split.

## Scope

- In: Age for managed squad players using squad-wide FM current date when per-player date fails
- In: Emit `loanClubId` / `loanClubName` when `loanedOut`
- In: Loans desk cards show loan club
- In: Player profile Club fact: loan club when set, parent as secondary
- Out: Wage/fee/expiry, inbound loans, T190 CA pack deltas

## Acceptance criteria

- [x] Loans desk cards show age when DOB is readable (squad game-date fallback)
- [x] Loans desk cards show loan club name
- [x] Profile Club shows loan club when player is loanedOut (parent still visible)

## Progress

### Shipped

1. Pre-scan squad for FM current date; use as fallback for age/season
2. `loanClubId` / `loanClubName` on live player JSON
3. Loans cards: age line + loan club line; profile: Loan club + `Parent: …`

### Verified

- `cargo test loaned_out_flag_uses_loan_club_mismatch`

### Commit

`356accf83696c62b88362ac77683d331d48c83b7`
