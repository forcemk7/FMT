---
id: T081
title: Faster loan motif search — same loan flags
status: blocked
priority: 4
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T086]
---

# T081 — Faster loan motif search — same loan flags

## Why

Loans is the honesty filter and the Squad split: outgoing stay off the HA table. `detect_loaned_out_jobs` still `find`s a 2-byte `64 ff` across the whole mmap, three times (FT / II / U19). That is likely most of the ~309s after decompress. The template pad is already required — search that, not `64 ff`.

Do **not** ship this during T083–T086 freeze. Speed is not the extract model.

## Scope

- In: same loan objects as **T082** (FT 7 / II 10 / U19 1 on König), same per-unit job sets
- In: find `LOAN_OUT_PAD` (then kind / club template), not a 2-byte prefix
- Out: new loan RE, shrinking the mmap window, changing who is `loanedOut`
- Out: favoured-club (T080), T077 host, world walks, live `games/*.fm`

## Acceptance criteria

- [ ] T082 counts still hold (FT 7, II 10, U19 1); Itu still at-club II
- [ ] Existing loan tests still pass (`tests/test_loan_detect_t040.py`, `tests/test_loan_detect_t012.py` if their bins exist)
- [ ] Progress records König `elapsedMs` before/after (human-run ok)
- [ ] One git commit `T081: …` on FMT/

## Notes / pointers

- `scripts/extract-first-team-fast.py` `detect_loaned_out_jobs` / `LOAN_OUT_PAD` / T040 list-adjacent `64ff24` skip
- T012 foreign U19 namelist path stays — do not drop it
- Never mmap live `Sports Interactive/games/*.fm`

## Progress

_(worker fills)_
