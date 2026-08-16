---
id: T086
title: At-club vs loaned-out on any Career Save
status: done
priority: 1
owner: worker
claimed_at: 2026-08-16
started_at: 2026-08-16T04:55:00+02:00
completed_at: 2026-08-16T05:20:00+02:00
depends_on: [T085]
---

# T086 — At-club vs loaned-out on any Career Save

## Why

This is the product. Mentoring Group checks and youth development are dishonest if a loaned player sits on Squad or an at-club player sits on Loans. Step 4: **contracts** — loan object on employed jobs. Launch (T077) waits until this split is honest on any Career Save.

## Scope

- In: loan object on FT/II/U19 jobs already listed. Same recipe all three units
- In: **Squad** = employed and at-club. **Loans** = employed and outgoing. **Mentoring** pool = Squad only (no Suggest)
- In: drop named-player loan skips and foreign-U19 namelist as law. `64ff24` stride is not a loan
- In: one PROGRESS/NDJSON **census** after the loan split (same Python, no second decompress): club id + name; each unit’s name; employed / at-club / loaned counts. UI already streams progress — do not build a new wizard
- Out: scan speed (T081). Favoured-club (T080). Live URL (T077). GK Progress layout (T087). Editing `.fm`. Committing `*.fm`. Fitting loan **counts**. A second extract. World entity scan (NG Regens 466k)

## Blind (non-negotiable)

- Do **not** git add `data/saves/` or `*.fm`. Do **not** mmap live `games/*.fm`
- Do **not** wait for another Career Save. Do **not** lock player names or loan counts into the detector
- Optional smoke on whatever `data/saves/*.fm` already exists. Honest empty Loans = nobody out, not a fail. Empty Squad after a real career extract = fail

## Acceptance criteria

- [x] A player is in **exactly one** of Squad or Loans (same name cannot be both)
- [x] Outgoing = loan object on a unit job; those names on Loans, not Squad, not Mentoring pool
- [x] `detect_loaned_out_via_foreign_u19` is not the required youth-loan path
- [x] Progress picker is the same people (at-club + loaned both OK to inspect; Group checks stay at-club)
- [x] Extract emits a census the human can check against FM before HA finishes filling: `clubId`, `clubName`, per unit `{ name, employed, atClub, loaned }` (missing unit omitted, not zero-filled from another save)
- [x] One git commit `T086: …` on FMT/ — no `.fm` in the commit

## Notes / pointers

- T082 cancelled — this ticket owns generic loans
- T040: list-adjacent `64ff24` is not a loan. Object rule, not a name skip
- Empty Loans on a career with no outgoing is honest. Empty **Squad** is not
- Copy-then-extract if you smoke a local file. Never mmap live `games/*.fm`

## Progress

Shipped: FT / II / U19 outgoing = `loan_hits_for_unit` (loan object on that unit’s jobs). Extract no longer calls `detect_loaned_out_via_foreign_u19`. Packed list-adjacent `64ff24` still rejected. One `phase=census` PROGRESS/NDJSON line after the split (clubId, clubName, per-unit employed/atClub/loaned; missing unit omitted). Squad / Mentoring pool = at-club; Loans = loanedOut; Progress picker = employed (at-club + outgoing).

Verified: `python -m unittest tests.test_loan_split_any_save_t086 tests.test_loan_detect_t040 tests.test_ha_ca_any_save_t085 tests.test_unit_squads_t084 tests.test_managed_club_identity_t083` (synthetic exclusive split, same recipe, stride reject, census omit, extract main does not call foreign-U19). Vitest squad-ha-table / loans-roster / extract-trust / mentoring-stack. Optional local smoke census to the human; not the recipe; no committed `.fm`.
