---
id: T182
title: Live Squad = at-club match squad only
status: done
priority: 1
owner: cursor-worker
claimed_at: "2026-08-27T15:12:00+02:00"
started_at: "2026-08-27T15:12:00+02:00"
completed_at: "2026-08-27T16:40:51+02:00"
depends_on: []
---

# T182 — Live Squad = at-club match squad only

## Why

Loop A Squad desk is usable for CA/PA/HAS triage, but the list still includes players **owned and out on loan**. Owner needs Squad = players **at club and available for match squads**. Loaned-out profiles belong elsewhere later (Loans desk) — not on Squad.

## Definition

- **On Squad:** managed club, currently at club (owned at club + inbound loan if present on the team list)
- **Off Squad:** owned but **out on loan** (parent club still owns them; they are not available here)
- Main club / at-club flag must be honest enough that we do not hide true at-club players or keep true outbound loans

## Scope

- In: Live Tauri path (`connector` → snapshot players) — classify outgoing loan vs at-club
- In: Emit a clear field (e.g. `loanedOut: bool`) **or** omit outbound from Squad payload
- In: `my-team-screen` (and any same club filter used for mentoring pool) keep at-club only
- In: Verify against owner’s loaded career: known outbound loans leave Squad; known at-club stay
- Out: Loans desk UI, sell/loan recommendations, development desk rewrite, unit FT/II/U19 taxonomy, savefile extract path, FMLE parity beyond at-club honesty

## Acceptance criteria

- [x] Squad no longer lists players the owner confirms are out on loan from the managed club
- [x] Squad still lists players the owner confirms are at club (including fringe / available to U19-Res if still at parent)
- [x] No Loans tab/desk required to pass this ticket — outbound may simply disappear from Squad until a later ticket

## Notes / pointers

- FMLE Parent Club vs Loan Club: parent stays on `person_contract`; Loan Club hangs off `person_loan_offset` (person+176 / +0xB0), adjacent to contract (+168)
- Locked live: Bora Eker → S.S.C. Napoli via loan obj → +0 → +0x10/+0x18 club
- Senior 43 → 5 loaned / 38 at-club on live probe

## Progress

### Shipped

1. `personLoanOffset: 176` in entity map + `read_person_loan_club_uid` / `loanedOut` emit
2. `isAtClubSquadPlayer` filters Squad, Dashboard, Mentoring
3. Live verify (`debug_live_loaned_out_contract_club`): LOANED_OUT = Lars Gabrielsen, Bora Eker, Ilan Kramarić, Alexandr Nusuev, Ivaylo Erinin (5); at_club=38

### Verified

- `cargo test loaned_out_flag_uses_loan_club_mismatch`
- `cargo test debug_live_loaned_out_contract_club -- --ignored` → 5/38
- `vitest` `live-data.test.ts`

### Commit

`c9806ed53e00cb38a7493db200ea706070bcfa38`
