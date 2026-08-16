---
id: T091
title: FT join must not stop on the first catalog hit
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-16T06:30:00+02:00
started_at: 2026-08-16T06:32:00+02:00
completed_at: 2026-08-16T06:48:00+02:00
depends_on: [T090]
---

# T091 — FT join must not stop on the first catalog hit

## Why

T083–T086 passed **synthetic** blobs. A real Career that is not the development (Schalke) save still yields an empty Squad. Identity can succeed, then `resolve_ft_squad` **returns on the first** PRE_NAME + short-name club object even when `find_ft_job_list` is None → `ft-club-squad-join-miss` / `no-job-list`. König’s first hit is lucky. Other clubs’ first hit is often a decoy object.

## Scope

- In: `ft_squad_discovery.py` `resolve_ft_squad` / `find_ft_job_list`. Keep scanning catalog hits until a club object **has a 7f02 job-list**. `BODY_HIT_LIMIT` is a search bound that **expands**, not a hard 200
- In: same idea for II/U19 if they also return the first name hit with `list: None` (do not require `{short} II`)
- Out: new save-named constants, MB windows as law, `pick_tid` when identity is known. T087. www. Editing `.fm`. Committing `*.fm`

## Blind (non-negotiable)

- Do **not** git add `data/saves/` or `*.fm`. Do **not** mmap live `games/*.fm`
- Do **not** put a real club name, UniqueID, or file offset from a local `.fm` into source as law
- Optional smoke: any untracked `data/saves/*.fm` that is **not** the Schalke/König copy. Report `ft_discovery_method` + `missReason` + job counts to the human. That run is not the recipe
- If the only `.fm` present is Schalke: still ship the first-hit continue; do not set blocked

## Acceptance criteria

- [x] `resolve_ft_squad` does not return the first team-object when `list` is missing; later catalog hits can still win a job-list
- [x] Identity known + true miss still `ft-club-squad-join-miss` (never `pick_tid`)
- [x] Unit test: two PRE_NAME + short-name objects; first has no 7f02 list, second has jobs → second wins
- [x] One git commit `T091: …` on FMT/ — no `.fm` in the commit

## Notes / pointers

```python
# ft_squad_discovery.resolve_ft_squad — current (wrong):
lst = find_ft_job_list(mm, team["teamId"], team["dup"])
return { ..., "list": lst }  # even if lst is None
```

Progress already prints `ft-club-squad-join-miss · {missReason}`. missReason: `no-catalog` | `no-team-object` | `no-job-list`.

## Progress

Shipped: `resolve_ft_squad` keeps scanning PRE_NAME + short-name catalog hits until a club object has a 7f02 job-list. `find_ft_job_list` / `find_ii_job_list` use `iter_hits` so `BODY_HIT_LIMIT` expands instead of capping at 200. II resolve skips catalog rows with `list: None` (U19 already continued). Identity known + true miss still `ft-club-squad-join-miss` / `no-job-list`, never `pick_tid`.

Verified: `python -m unittest tests.test_ft_join_first_hit_t091 tests.test_unit_squads_t084 tests.test_match_reserve_name_score_t090 tests.test_managed_club_identity_t083 tests.test_ha_ca_any_save_t085 tests.test_loan_split_any_save_t086` — 38 tests OK. Optional smoke: the only non-Schalke `data/saves/*.fm` is not a readable career zstd (decompress failed); Schalke copies skipped as required. Not blocked. No committed `.fm`.
