---
id: T093
title: Native FM26 this-club squad list (not continue 7f02)
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-16T07:33:00+02:00
started_at: 2026-08-16T07:34:00+02:00
completed_at: 2026-08-16T07:50:00+02:00
depends_on: [T092]
---

# T093 — Native FM26 this-club squad list (not continue 7f02)

## Why

Manage saves showing **club id + name** with **0 players** is expected today: identity (T083) writes `clubId` / `clubName` even when `players[]` is empty.

Schalke works because it is **FM24 continued in FM26**. The other Careers are **native FM26**. Continue uses the König club-object `7f02…ffffffff` list. Native identity tag is `00 95 0e 01`; continue is `00 95 0e 02`. When identity is known, extract **skips** `walk_world_squads_if_needed` — so the native list parser already in `parse_squad_candidates` (layout B `010302`) never runs for those saves. T092 loosened the **continue** join. Native still 0 jobs.

Two recipes in **one** Python, switched on detected layout. Not two apps. Not `pick_tid`.

## Scope

- In: detect layout from identity `tagHex` / `inferredLayout` (`fm24_continue_style_zstd_at_26` vs native)
- In: **continue** path unchanged (Schalke still has a Squad)
- In: **native** path: this club’s FT (and II/U19 if the same list family) via `parse_squad_candidates` / `010302` keyed by identity **clubId** — do not skip native list discovery because identity is known; do not walk every club in the save (T076)
- In: `SQUAD_COUNT_LO/HI` 11–55 in `try_jobs_at` is not law for native
- Out: `pick_tid`. World staff/stadium walk. New MB/UID/name constants from one native `.fm`. T087. www. Committing `*.fm`

## Blind (non-negotiable)

- Do **not** git add `data/saves/` or `*.fm`. Do **not** mmap live `games/*.fm`
- Do **not** copy a native save’s offsets into source
- Optional smoke: a native FM26 `.fm` that decompresses. Report layout + `jobsFound`. Truncated files are not a pass

## Acceptance criteria

- [x] Layout is explicit on PROGRESS (`continue` | `native`)
- [x] Synthetic native blob (identity tag `00950e01` + `7f02`+`010302` list, no `ffffffff`) yields FT jobs for that clubId
- [x] Synthetic continue blob (tag `00950e02` + `7f02…ffffffff`) still yields FT jobs (Schalke-class regression)
- [x] Identity known + native miss still `ft-club-squad-join-miss`, never `pick_tid`
- [x] One git commit `T093: …` on FMT/ — no `.fm` in the commit

## Notes / pointers

- `extract-managed-team.py` `HUMAN_TAGS`: `00950e01` native, `00950e02` continue
- `parse_squad_candidates` layouts A (continue ff) vs B (native 010302) already exist; club-object join never called them for identity-known saves
- `walk_world_squads_if_needed`: `if club_short: return skipped_identity_known`
- Dropdown club line = extract identity fields, not proof the squad join hit

## Progress

Shipped: two recipes in one Python. Layout from identity `tagHex` (`00950e01` native / `00950e02` continue) with `inferredLayout` fallback; PROGRESS `layout` is `continue` | `native`. Continue still uses club-object `7f02…ffffffff` (`resolve_ft_squad`). Native identity-known no longer skips list discovery: this club’s UniqueID immediately before `7f02`+`010302` via `parse_squad_candidates` (`SQUAD_COUNT` 11–55 is not law). World 7f02 walk still skipped (T076). Identity known + native miss still `ft-club-squad-join-miss`, never `pick_tid`.

Verified: `python -m unittest tests.test_native_fm26_squad_list_t093 tests.test_ft_join_clubid_native_t092 tests.test_ft_join_first_hit_t091 tests.test_unit_squads_t084 tests.test_world_lists_skip_t076 tests.test_managed_club_identity_t083 tests.test_roster_employees_only_t009 tests.test_ft_club_squad_join_t006 tests.test_match_reserve_name_score_t090 tests.test_ha_ca_any_save_t085 tests.test_loan_split_any_save_t086` — 55 tests OK (7 skipped: live-bin). Optional smoke not run (truncated `.fm` is not a pass). No committed `.fm`. Restart `npm run dev` and re-extract a native FM26 career.
