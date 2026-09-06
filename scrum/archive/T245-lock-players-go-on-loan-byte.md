---
id: T245
title: Lock Players-Go-On-Loan affiliation byte
status: done
priority: 1
owner: auto
claimed_at: "2026-09-06T22:27:00+02:00"
started_at: "2026-09-06T22:27:00+02:00"
completed_at: "2026-09-06T22:50:00+02:00"
depends_on: [T244]
---

# T245 — Lock Players-Go-On-Loan affiliation byte

## Why

Match experience still loads feeders without a loan agreement (Daegu, Melbourne). Need one locked byte, then a simple production read — **not** runtime name-needle diffs.

## Scope

- In: RE once — dump `club+0x118` wrapper/nested hex; diff loan-on (Legia / Sparta / KL) vs loan-off (Daegu / Melbourne); lock offset + on/off in `research/recipes.md`
- In: Production filter = read that byte only; remove T242 Schalke needle auto-diff / candidate lock from load path
- Out: ME card chrome (T244); inventing PGE string for AffiliationType `0x03`; FMLE paid Save Changes as the only method (ok as A/B evidence)

## Acceptance criteria

- [x] recipes.md documents locked region+offset and on/off values with Schalke evidence
- [x] Load skips feeders whose loan byte ≠ on-value
- [x] No production runtime “find separators from club names”
- [x] Commit `T245: …`

## Progress

Locked: **nested+0x65** loanOn=`1` loanOff=`0` (live Diagnostics 2026-09-06). Hardcoded `PLAYERS_GO_ON_LOAN_*` + `nested_players_go_on_loan`; name-needle auto-diff removed from load path. recipes.md updated.

Commit: `_(fill)_`
