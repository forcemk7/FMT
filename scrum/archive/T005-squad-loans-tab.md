---
id: T005
title: "INTEGRATE: Loans tab wiring in main.ts"
status: done
priority: 2
owner: auto
claimed_at: "2026-08-11T21:56:00+02:00"
started_at: "2026-08-11T21:56:00+02:00"
completed_at: "2026-08-11T22:02:00+02:00"
depends_on: [T005A, T005B]
---

# T005 — INTEGRATE: Loans tab wiring in main.ts

## Why

Club-wide Out on loan belongs on its own tab. Last step after T005A + T005B. T006 unblocked honest FT verification.

## Scope

- In: `SquadViewMode` += `"loans"`; hash `#roster/loans`; tab active states; render Loans view using T005A helpers + T005B chrome
- In: personality cards per section with loan club crest via existing `bindClubLogo` / loan badge helpers
- In: remove FT/II/U19 personality “Out on loan” divider strip (loans live on Loans tab only) — avoid duplicate surfaces
- Out: new detect; Millwood motif RE; Dynamics; sync pill

## Acceptance criteria

- [x] Tab works: First Team / Reserves / Under 19s / Loans / Mentoring
- [x] Loans view shows only `loanedOut`, grouped FT → Reserves → U19
- [x] Crest when `loanClubId` available
- [x] Unit personality pages no longer append the loan divider block
- [x] Empty club / no loans: sensible empty state
- [x] Mark done per AGENTS.md before final reply

## Claim rule

Claim only when **T005A and T005B are both `done`**. One agent. Stay inside SCOPE.md.

## Notes

- Pointers: `createSquadPersonalityCard`, `playerLoanBadgeClubId`, `.squad-loan-crest`, archived T004 detect
- Millwood may be absent until a future detect ticket — do not block T005 on him

## Progress

- 2026-08-11: claimed; T005A+B archived — wired `main.ts`.
- **Done.** `SquadViewMode` += `loans`; `#roster/loans`; `renderLoansPage()` via `loansByUnit`; panel `is-loans`; unit grids filter out `loanedOut` (no divider strip); empty → `#squad-loans-empty`. Crest via existing `createSquadPersonalityCard` / `playerLoanBadgeClubId`. Clicking a Loans card picks the owning unit before Attributes. Verified: `vitest tests/loans-roster.test.ts` 9/9; no new main.ts lint/tsc issues.
