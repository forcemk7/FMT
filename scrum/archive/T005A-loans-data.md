---
id: T005A
title: "Loans tab data: loanedOut by unit + helpers"
status: done
priority: 1
owner: auto
claimed_at: "2026-08-11T21:39:27"
started_at: "2026-08-11T21:39:27"
completed_at: "2026-08-11T21:40:57"
depends_on: [T006]
---

# T005A — Loans tab data: loanedOut by unit + helpers

## Why

T005 needs a single club-wide loan list split FT / Reserves / U19 without each page inventing filters. T006 fixed FT club honesty — reopen.

## Scope

- In: new small module (prefer `web/loans-roster.ts`) exporting pure helpers, e.g.:
  - `loanedOutPlayers(unitPlayers)` → players with `loan.status === "loanedOut"` only (not loanedIn)
  - `loansByUnit({ firstTeam, reserves, under19s })` → `{ firstTeam, reserves, under19s }` arrays
  - optional: stable sort (HAS score if signals exist, else name) — mirror squad personality ranking if cheap; else name sort + document
  - `loanCrestClubId(player)` / reuse existing loan club id helper contract documented in Progress
- In: vitest coverage for empty / FT-only / multi-unit / ignores loanedIn
- Out: HTML/CSS; `web/main.ts` wiring; extract/detect; Mentoring

## Acceptance criteria

- [x] Module exists and is importable from web tests
- [x] Tests prove loanedOut-only + unit bucketing
- [x] Progress documents exact export names + sort rule for T005 integrator
- [x] **No** `web/main.ts` / `web/index.html` / extract edits

## Claim rule

One agent. Spikes/tests/new module only. Do not steal T005B’s HTML/CSS.

## Progress

- 2026-08-11: paused for T006; **reopened ready** after T006 done.
- 2026-08-11: claimed + in_progress — shipping `web/loans-roster.ts` + vitest.
- 2026-08-11: **done.** Shipped `web/loans-roster.ts` + `tests/loans-roster.test.ts` (9 passed). No main/HTML/extract edits.

### Exports for T005 integrator

| Export | Contract |
|--------|----------|
| `loanedOutPlayers(unitPlayers)` | Filter `loan.status === "loanedOut"` only; returns new name-sorted array |
| `loansByUnit({ firstTeam, reserves, under19s })` | Same filter per unit → `{ firstTeam, reserves, under19s }` |
| `loanCrestClubId(player)` | `loanedOut` → finite `loan.loanClubId`, else `null`. Matches main.ts `playerLoanBadgeClubId` loanedOut branch. loanedIn/atClub → `null` |

### Sort rule

**Name sort** (`localeCompare` base sensitivity). HAS ranking is not mirrored here — it depends on private `estimatesFromPersonalitySignals` in `main.ts`. T005 may re-sort by HAS at render if desired.
