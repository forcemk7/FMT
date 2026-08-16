---
id: T099
title: Game date is u16 doy + u16 year after UniqueID
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-16
started_at: 2026-08-16
completed_at: 2026-08-16
depends_on: [T097]
---

# T099 — Game date is u16 doy + u16 year after UniqueID

## Why

T097 reads `tail[1]` as a `u8` doy. That only matched one save where both bytes were `04`. Owner-checked four Careers: year is always `u16` at UniqueID+6; doy is the `u16` at UniqueID+4 (363 on one save — not a `u8`). One save’s doy word is `0x0404` (1028); `1028 & 0x1FF == 4`. T098’s “u8 before year” is cancelled.

## Scope

- In: replace `pick_game_date_near_identity` only:

```
year = u16 LE at UniqueID + 6
raw  = u16 LE at UniqueID + 4
doy  = raw if 1 ≤ raw ≤ 366 else (raw & 0x1FF)
if year in 2020..2050 and 1 ≤ doy ≤ 366:
    gameDate = date(year, 1, 1) + (doy - 1)
else:
    gameDate = None   # UI —
```

- In: unittest those four shapes (no `.fm`). Identity club parse unchanged.
- Out: dump files, Manage saves chrome, auto-sync, 24MB calendar, squad/HA, searching a tail window, hardcoded club/iso. T087. `*.fm` / `tmp/` in git

## Blind (non-negotiable)

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Do **not** mmap live `games/*.fm`
- Do **not** put club names or real save dates in source as law — only the struct + synthetic numbers

## Acceptance criteria

- [x] `doy = tail_bytes[1]` is gone
- [x] Synthetic UniqueID + `pack("<HH", 4, 2026)` → 2026-01-04
- [x] Synthetic UniqueID + `pack("<HH", 0x0404, 2026)` → 2026-01-04 (not 4 Apr)
- [x] Synthetic UniqueID + `pack("<HH", 363, 2025)` → 2025-12-29 (not 2025-01-01, not 2025-04-17)
- [x] Synthetic UniqueID + `pack("<HH", 1, 2026)` → 2026-01-01
- [x] One git commit `T099: …` on FMT/ — no `.fm`, no `tmp/`

## Notes / pointers

- `scripts/extract-managed-team.py` `pick_game_date_near_identity`
- Skip dump refresh, vitest chrome, extra tickets. Parser + unit tests + commit.

## Progress

Shipped: `pick_game_date_near_identity` reads u16 LE year at UniqueID+6 and u16 LE raw at UniqueID+4. `doy = raw` if 1..366 else `raw & 0x1FF`. `date(year, 1, 1)+(doy-1)`; invalid → —. `tail_bytes[1]` gone. Identity club parse unchanged. No dump refresh, no UI.

Verified: `python -m unittest tests.test_identity_game_date_t099 tests.test_identity_game_date_t097 tests.test_identity_game_date_t096 tests.test_managed_club_identity_t083` (22 ok). Four pack("<HH") shapes: 4/2026 → 2026-01-04; 0x0404/2026 → 2026-01-04 not 4 Apr; 363/2025 → 2025-12-29 not 1 Jan / 17 Apr; 1/2026 → 2026-01-01. No committed `.fm` / `tmp/`.

Owner: + four Career Saves and say if In-game matches FM. Then freeze unless unfrozen.
