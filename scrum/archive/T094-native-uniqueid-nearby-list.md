---
id: T094
title: Native UniqueID nearby 7f02 list (not glued)
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-16T08:05:00+02:00
started_at: 2026-08-16T08:08:00+02:00
completed_at: 2026-08-16T08:20:00+02:00
depends_on: [T093]
---

# T094 — Native UniqueID nearby 7f02 list (not glued)

## Why

T093 shipped two recipes. Continue Schalke still has a Squad. **Native FM26 still shows club id + name and 0 players.** T093 native join is `struct.pack("<I", club_id) + LIST_SENTINEL_LOOSE` — UniqueID **immediately** before `7f02`. That glued needle is a synthetic assumption. Real native club objects put fields between UniqueID and the job list. Identity is already correct; this-club list discovery still misses.

Empty UI with `jobsFound: 0` is this ticket. If `jobsFound > 0` and the table is still empty, **stop and report** (names / T042) — that is not T094.

## Scope

- In: **native** path only (`layout == native`). Find this club’s UniqueID, then a **nearby** `7f02`+`010302` list (`parse_squad_candidates` / `_native_list_at_sentinel`). Gap expands; glued T093 case still hits
- In: same list family for II/U19 if those lists sit on the same club object (empty subunit if missing — T084)
- In: continue path unchanged (`resolve_ft_squad` / `7f02…ffffffff`)
- In: PROGRESS still `layout` + `jobsFound` (0 jobs vs 0 names stays visible)
- Out: `pick_tid`. Walking every club’s `7f02` (T076). New MB / UID / count / gap constants copied from one native `.fm`. T087. www. Committing `*.fm`

## Blind (non-negotiable)

- Do **not** git add `data/saves/` or `*.fm`. Do **not** mmap live `games/*.fm`
- Do **not** copy a native save’s offsets, club ids, or measured gap into source as law
- Optional smoke: a native FM26 `.fm` that **decompresses**. Report `layout` + `jobsFound`. Truncated files are not a pass

## Acceptance criteria

- [x] Synthetic native blob: UniqueID, **padding bytes**, then `7f02`+`010302` list → FT jobs for that clubId (glued UniqueID|`7f02` still works)
- [x] Synthetic continue blob (tag `00950e02` + `7f02…ffffffff`) still yields FT jobs
- [x] Identity known + native miss still `ft-club-squad-join-miss`, never `pick_tid`
- [x] Optional smoke: if `jobsFound > 0` and UI empty, stop and report — do not keep hunting lists
- [x] One git commit `T094: …` on FMT/ — no `.fm` in the commit

## Notes / pointers

- `resolve_native_ft_squad` in `scripts/extract-first-team-fast.py`: glued needle is the miss. Search UniqueID occurrences, then scan **forward** (bounded, expanding) for `LIST_SENTINEL_LOOSE`; do not iterate every `7f02` in the file
- Continue already expands list windows (`find_ft_job_list`); steal that pattern for UniqueID → list gap, do not invent a world dump
- `SQUAD_COUNT_LO/HI` 11–55 and `filter_jobs` magnitudes are continue-shaped — not law for native. If a list parses then jobs are dropped, report that; do not silently empty the table
- Dropdown club line = identity (T083), not proof the squad join hit
- T087 stays frozen until a native extract writes a non-empty `players[]`

## Progress

Shipped: native FT join is UniqueID occurrences, then expanding forward `LIST_WINDOWS` (same as continue) for `7f02`+`010302`. Glued UniqueID|`7f02` still hits. Padding between UniqueID and the list uses `tid_hint` when the 4 bytes before `7f02` are not a persist tid. Does not walk every `7f02` in the file. Continue `resolve_ft_squad` unchanged. Identity known + miss still `ft-club-squad-join-miss`, never `pick_tid`. II/U19 stay T084 empty-if-missing on the existing club-short join.

Verified: `python -m unittest tests.test_native_uniqueid_nearby_list_t094 tests.test_native_fm26_squad_list_t093 tests.test_ft_join_clubid_native_t092 tests.test_ft_join_first_hit_t091 tests.test_unit_squads_t084 tests.test_world_lists_skip_t076 tests.test_managed_club_identity_t083 tests.test_roster_employees_only_t009 tests.test_ft_club_squad_join_t006 tests.test_match_reserve_name_score_t090 tests.test_ha_ca_any_save_t085 tests.test_loan_split_any_save_t086` — 59 tests OK (7 skipped: live-bin). Optional smoke not run (no usable native `.fm` in this pass). No committed `.fm`. Restart `npm run dev` and re-extract a native FM26 career. If `jobsFound > 0` and Squad is still empty, that is names/T042 — not another list hunt.
