---
id: T092
title: FT list from club UniqueID and native 7f02 shape
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-16T06:52:00+02:00
started_at: 2026-08-16T06:53:00+02:00
completed_at: 2026-08-16T07:20:00+02:00
depends_on: [T091]
---

# T092 — FT list from club UniqueID and native 7f02 shape

## Why

T091 skipped decoy catalog **name** hits. Other Careers still resolve **0 players**. T091 smoke never ran a readable non-Schalke zstd. The join is still König-shaped: UTF-8 `parent_short` + PRE_NAME + team body `00×10` + `7f02…ffffffff` within **128** bytes (`data/fixtures/ft-club-squad-join-locked.json`). Native FM26 already has `LIST_SENTINEL_LOOSE` + `010302` in `extract-first-team-fast.py`; FT discovery does not use them. Identity already has **club UniqueID** (T083) — stop depending on the short-name string as the only key.

## Scope

- In: `ft_squad_discovery.py` (+ extract resolve). Primary key = identity **clubId**. Short-name catalog search is fallback
- In: First Team list shape = persist-tid + `7f02` job-list. `ffffffff` tail and +128 window and 10-zero body are **heuristics that expand** (use loose `7f02` / `010302` when the strict sentinel misses)
- In: PROGRESS on miss/hit: `clubId`, `missReason`, `catalogHits`, `teamObjects`, `jobsFound` (so 0 players vs 0 jobs is visible)
- Out: `pick_tid` when identity is known. New club-id / name / MB constants from a local `.fm`. T087. www. Committing `*.fm`

## Blind (non-negotiable)

- Do **not** git add `data/saves/` or `*.fm`. Do **not** mmap live `games/*.fm`
- Do **not** copy offsets from a second Career into source
- Optional smoke on an untracked non-Schalke `data/saves/*.fm` that **decompresses**. Truncated/unreadable files are not a pass. Report jobsFound + missReason. Not the recipe

## Acceptance criteria

- [x] Synthetic: clubId on the club object finds the 7f02 list when the short-name row is absent or decoy
- [x] Synthetic: list parses with loose `7f02` (no `ffffffff`) / `010302` when the strict sentinel is missing
- [x] Identity known + true miss still `ft-club-squad-join-miss` (never `pick_tid`)
- [x] Progress JSON includes `jobsFound` (0 vs N) on the resolve line
- [x] One git commit `T092: …` on FMT/ — no `.fm` in the commit

## Notes / pointers

- Fixture still says mid-file 40–100MB and count 15–45 — those are **not** law (T084). Do not re-add them
- `LIST_SENTINEL` vs `LIST_SENTINEL_LOOSE` / `TAG_010302` in `extract-first-team-fast.py`
- II already reads clubId after the name (`CLUB_ID_REL`); FT should use the same UniqueID the identity parser already returned
- If jobsFound > 0 but the UI is empty, stop and report (name-table band is a **different** ticket)

## Progress

Shipped: `resolve_ft_squad` takes identity club UniqueID as the primary catalog key (PRE_NAME object with UniqueID after the name, same after-name slot as II). UTF-8 parent_short is fallback. `find_ft_job_list` expands past `ffffffff` / +128 / 10-zero body: `LIST_SENTINEL_LOOSE` and `TAG_010302` parse persist-tid jobs when the strict sentinel misses. Identity known (short or UniqueID) + miss still `ft-club-squad-join-miss`, never `pick_tid`. Resolve PROGRESS includes `clubId`, `missReason`, `catalogHits`, `teamObjects`, `jobsFound`.

Verified: `python -m unittest tests.test_ft_join_clubid_native_t092 tests.test_ft_join_first_hit_t091 tests.test_unit_squads_t084 tests.test_match_reserve_name_score_t090 tests.test_managed_club_identity_t083 tests.test_ha_ca_any_save_t085 tests.test_loan_split_any_save_t086 tests.test_roster_employees_only_t009 tests.test_ft_club_squad_join_t006` — 49 tests OK (7 skipped: live-bin). Optional smoke not run (truncated `.fm` is not a pass). No committed `.fm`. Restart `npm run dev` and re-extract a non-Schalke career.
