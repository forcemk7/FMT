---
id: T002
title: Wire locked Dynamics (cap + social + list order); hierarchy may be null
status: done
priority: 2
owner: auto
claimed_at: 2026-08-13T13:05:00Z
started_at: 2026-08-13T13:05:00Z
completed_at: 2026-08-13T13:12:00Z
depends_on: []
---

# T002 — Wire what is already locked; stop waiting on hierarchy enum

## Why

**Loop break (behavior):** T001 has **zero product change** after days of hierarchy hunt. User: stop waiting. Captaincy + social membership are **already lockable** (`data/fixtures/dynamics-layout-spike-notes.md`). Social lists are **hierarchy-sorted within group** — use **list order as rank proxy**. 4-tier enum can stay `null`. Manual hierarchy labels remain override.

## Scope

- In: extract `dynamics.captaincy`, `dynamics.socialGroup`, `dynamics.socialRank` (index in that social list, 0 = highest in-group) for FT
- In: `hierarchy` = null unless T001 later locks the enum
- In: types + a fixture check vs GT membership (not enum)
- Out: inventing Team Leader vs Highly Influential from order alone as FM labels; Mentoring Suggest rewrite (T003); T014; T032 UX

## Acceptance criteria

- [x] Re-extract of dynamics A/B (or current Schalke save) fills captaincy + social group matching screenshot GT
- [x] Social list order exported per player (rank in Core / Secondary / Other)
- [x] `hierarchy` is null or omitted — no fake TL/HI
- [x] Web types accept the payload; extract does not crash if motif missing (fields null)

## Notes / pointers

- Spike notes: cap tail after FT job list; social motif `b5 1a e7 07 01 f7 02 00 00`
- `scripts/extract-first-team-fast.py`
- T001 may keep hunting enum in parallel — this ticket does **not** wait

## Progress

Shipped FT extract of captaincy (job-list tail), social group (motif counted lists), and `socialRank` (index in that list, 0 = highest in-group). `hierarchy` always null. Wired in `extract-first-team-fast.py` `apply_ft_dynamics` after FT player build. `PlayerDynamics.socialRank` added; roster pass-through accepts the payload.

Verified: `python -m unittest tests.test_dynamics_extract_t002 -v` (4 OK) — synthetic missing-motif stays null / no crash; A/B bins match screenshot GT membership + list order (A Tusjak/Paco, B Gilson/Radović). `npx vitest run tests/dynamics-payload.test.ts` OK.

Residual: 4-tier hierarchy still T001; Mentoring Suggest does not consume extract dynamics yet (T003).
