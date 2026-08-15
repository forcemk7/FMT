---
id: T076
title: Extract this club’s players — not the whole save
status: done
priority: 4
owner: cursor-agent
claimed_at: 2026-08-15T14:18:00+02:00
started_at: 2026-08-15T14:25:00+02:00
completed_at: 2026-08-15T14:40:00+02:00
depends_on: [T069]
---

# T076 — Extract this club’s players — not the whole save

## Why

The wedge vs Genie Scout is HA/CA for **this club** without loading every player, staff, and stadium. T072 already cut multi-Python on start. This ticket is: do not spend extract time on world objects the three tabs never show.

## Scope

- In: extract path used by `npm run dev` for Squad / Loans / Mentoring / Progress
- In: FT + II + U19 identity, pack HA, Det/Lea, CA; loan flag (Squad = at-club, Loans = outgoing)
- Out: staff, stadiums, full-world scouting dump, new RE rabbit holes, FM27
- Out: “make it feel fast” with no before/after on this save

## Acceptance criteria

- [x] Squad / Loans / Mentoring / Progress still populate for the König (or current) save
- [x] Extract no longer walks staff/stadium (or equivalent world) lists this club’s tabs do not use — note in Progress what was skipped
- [x] One git commit `T076: …` on FMT/
- [x] Progress records rough before/after duration on the same save (human-run ok)

## Notes / pointers

- Never mmap live `games/*.fm`
- T068 U19 before-name list and FT CA strip stay
- If already skipped, ticket is: prove it in Progress and stop — do not invent a second extractor

## Progress

Same extractor (`extract-first-team-fast.py`). When managed-club identity is known, skip all-club `7f02` squad discovery (including giant staff dumps) and manager/staff-link ranking for foreign teamIds. Stadiums were never walked. Fallback pick_tid walk remains only if identity is missing. Not a second extractor. Live `Sports Interactive/games/*.fm` still refused.

König `data/saves` Career Save (copy, not live games): FT 34 / II 30 / U19 30, same UIDs and jobIds, U19 before-name Δ−185, 16 loanedOut, 33 FT Det/Lea + CA, gameDate 2040-01-13, method `ft-club-squad-join-v1`.

Before: 372s (`elapsedMs` 371652). Decompress ~18.5s then ~32s world staff-link scan (identity at 51s).
After: 316s (`elapsedMs` 315801). Decompress ~6.7s, skip world lists, identity at 6.7s. About 56s faster on this save. Player attr scan is still most of the time.

Verified: `python -m unittest tests.test_world_lists_skip_t076` plus the two König extracts above. Restart `npm run dev` to pick up the skip.
