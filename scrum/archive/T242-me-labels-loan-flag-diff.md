---
id: T242
title: ME affiliate labels + loan-flag wrapper diff
status: done
priority: 1
owner: auto
claimed_at: "2026-09-06T21:05:00+02:00"
started_at: "2026-09-06T21:05:00+02:00"
completed_at: "2026-09-06T21:20:00+02:00"
depends_on: [T241]
---

# T242 — ME affiliate labels + loan-flag wrapper diff

## Why

Duplicate affiliate card titles (two Legia / two Sparta). Need `{clubName} {TeamType}`. Also exclude feeders without “Players Go On Loan” by static-diffing loan (Legia/Sparta/KL) vs no-loan (Daegu/Melbourne) wrapper bytes on `club+0x118`.

## Scope

- In: Match experience labels for affiliates = club name + TeamType (Squad desk unchanged)
- In: Dump wrapper (+ nested) hex on affiliation walk; resolve partner names; static-diff loan vs no-loan needles; warn candidate offsets; filter `0x03`/`0x01` load when a stable loan-on byte is found
- Out: FMLE paid A/B; inventing PGE string name for 0x03

## Acceptance criteria

- [x] ME cards show distinct titles for feeder First vs Under N
- [x] Affiliation report includes wrapper hex per link
- [x] Diff helper unit-tested; production warns candidates and filters when lock is confident
- [x] recipes.md notes loan-flag hunt
- [x] Commit `T242: …`

## Progress

Shipped:

- `matchExperienceTeamLabel` — affiliates `{clubName} {TeamType}`; managed teams keep `squadTeamDisplayName`
- Wrapper `0x80` / nested `0x40` hex on affiliation walk report
- `find_stable_u8_separators` + Schalke on/off name needles; `loanFlagLock` only on boolean 0/1 separator; filter feeder load when locked
- Diagnostics warnings for lock or candidate counts
- recipes.md Open note for Players Go On Loan hunt

Verified: vitest match-experience (10); cargo `schalke_loan_needles` + `stable_u8_separator_finds_loan_flag`.

Commit: `54798d9`
