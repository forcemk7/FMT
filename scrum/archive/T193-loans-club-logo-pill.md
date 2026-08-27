---
id: T193
title: Loans club logo pill + profile active-club logo
status: done
priority: 1
owner: cursor-worker
claimed_at: "2026-08-27T22:32:00+02:00"
started_at: "2026-08-27T22:33:00+02:00"
completed_at: "2026-08-27T22:40:00+02:00"
depends_on: [T191]
---

# T193 — Loans club logo pill + profile active-club logo

## Why

Loans cards bury loan club in the text stack. Profile shows loan club name but logo still falls back to parent when the loan club is missing from `snapshot.clubs`.

## Scope

- In: Loans cards — loan club as logo+name pill on the name row (right of name)
- In: Profile Club fact — logo uses active club id (loan if set, else parent); do not fall back logo to parent when loaned
- Out: Wage/fee, inbound loans, GM desk

## Acceptance criteria

- [x] Loans desk cards: loan club is a combined logo + name pill to the right of the player name (not a text line under age)
- [x] Player profile: when `loanedOut` + `loanClubId`, ClubLogo uses loan club id; parent remains subtitle only

## Progress

### Shipped

1. Loans cards: name row with logo+name pill (`loanClubId` → `ClubLogo`); removed under-age text line
2. Profile: `activeClubId` / `activeClubName` drive logo + label; no parentClub logo fallback when loaned; Parent stays subtitle; click still requires club in snapshot

### Verified

- Lint clean on touched TSX
- Visual: reload Loans desk + open a loanee profile after `desktop:stable`

### Commit

_(SHA after commit)_
