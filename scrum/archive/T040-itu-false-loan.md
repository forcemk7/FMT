---
id: T040
title: INCIDENT — Adrian Itu missing from HA table (false U19 loan)
status: done
priority: 1
owner: auto
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: []
---

# T040 — At-club II must not be shown as a U19 outgoing loan

## Why

**Loop:** club HA table is the squad you mentor from. User GT (locked): **Adrian Itu is not on loan. He is in the II squad.** FMT does not show him on the Personalities HA list and instead shows him on **Loans → Under 19s** with a **Schalke** crest. `mergeClubWideAtClubPlayers` drops `loanedOut`, so a false tag hides an at-club II body. Inverse of T012 (real U19 loans pulled off the at-club grid). Likely II false `loanedOut` then `rehome_loaned_newgen_to_u19` (II NEWGEN + high host id → U19 Loans).

## Scope

- In: Current Schalke Career Save. Resolve Itu (uid, extract unit, `loan` payload, tag path: motif / foreign-U19 attach / II→U19 rehome)
- In: Untag / un-rehome so he is **at-club II**: on the club HA table (Unit **II**), in the Mentoring pool, **not** on Loans
- In: Schalke crest on that Loans card is the same lie (parent/affiliate id) — fix classification, not logo polish
- In: Same class: at-club II (or FT) bodies tagged `loanedOut` and sitting on Loans → U19. Don’t stop at one name if the detect/rehome is shared
- In: Regression: known true outgoing U19 loans stay on Loans (T012: Millwood, Boxleitner, Davyskiba, Kasprakov) and off the HA table
- Out: T039. Suggest. Crest art. Open-ended loan RE. CA/PA. Dual-reg as a new product

## Acceptance criteria

- [x] Itu is on the club Personalities HA table with Unit **II**
- [x] Itu is **not** on Loans → Under 19s (FM: not outgoing)
- [x] T012 U19 outgoing set does not regress onto the HA table
- [x] User can check Itu’s HA / capture a unit like any other at-club II player

## Notes / pointers

- User GT: **not on loan; II squad;** missing from HA; incorrectly U19 loaned-out + Schalke logo
- Probe UID `2002158957` in `scripts/_probe-ha-pack-history.py` — **may be wrong**; resolve from extract name
- Extract suspects: `detect_loaned_out_jobs`, `detect_loaned_out_via_foreign_u19` (T012), **`rehome_loaned_newgen_to_u19`** (moves II NEWGEN `loanedOut` with clubId >200k onto U19)
- Motif already rejects `c1 == parent_club` (920). Schalke crest ⇒ affiliate II id, youth host that still paints Schalke, or logo-index collision — still a classification bug
- UI: `mergeClubWideAtClubPlayers` skips `loanedOut`; Loans = `loanedOutPlayers` only
- Dynamics WIP: Itu left FT Others — consistent with II, not with a foreign loan
- Do not steal T039

## Progress

### Shipped

1. Resolved Itu on König save: uid **2002400248**, job **516374**, II namelist (not U19), NEWGEN.
2. Tag path: II `detect_loaned_out_jobs` hit club **3609393** (lookback 25) → `rehome_loaned_newgen_to_u19` because NEWGEN + host >200k. Not foreign-U19 attach.
3. 3609393 is the **next team-body dup**, not a loan club. The II job array is followed by a `64 ff 24` team object that satisfies the loan pad+template; closest unit job is the last II body (Itu). Schalke crest = logo collision on that dup. Same class as T012 Boxleitner’s 3609393 “host”.
4. **Fix:** `detect_loaned_out_jobs` skips templates whose lookback is a packed subunit job-list (4-byte stride run ≥ 3). True loans stay at 1 job in lookback (Konya noise = 2). Shared for FT/II/U19 last-on-list FPs.
5. Tests: `tests/test_loan_detect_t040.py` — synthetic packed-list reject + isolated loan keep; König bin: Itu untagged / not rehomed; Millwood 2589, Davyskiba, Kasprakov 877204 still tagged; Manole/Zetzmann/Dunkel still II loans.

### Verified

- `python -m unittest tests.test_loan_detect_t040 tests.test_loan_detect_t012 -v` — T040 9 ok; T012 skipped (`live-0112-decomp.bin` missing).
- HA/Mentoring: existing `mergeClubWideAtClubPlayers` / pool already drop only `loanedOut` — untag is enough. Re-upload Career Save to see Itu on Personalities as **II**.

### Residual risk

- Boxleitner is on the U19 namelist this save with **no** loan motif (already at-club U19 in extract, independent of T040). Millwood / Davyskiba / Kasprakov remain outgoing.
- T012 Boxleitner lock on live-0112 used this same team-dup FP with a singleton job set; full II scan now rejects it. Don’t revive the FP.
- Re-extract required for the in-app table.
