---
id: T090
title: Define match_reserve_name_score so extract runs
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-16T06:06:00+02:00
started_at: 2026-08-16T06:07:00+02:00
completed_at: 2026-08-16T06:12:00+02:00
depends_on: []
---

# T090 — Define match_reserve_name_score so extract runs

## Why

Extract dies: `NameError: name 'match_reserve_name_score' is not defined`. Squad / Loans / Mentoring / Progress never load. T084 fuzzy reserve join calls a function that was never defined — its body is dead code after `return None` in `lp32_name_ending_at`.

## Scope

- In: `scripts/ii_squad_discovery.py` only. Add `match_reserve_name_score(parent_short, name)` using existing `_reserve_suffix` + `match_unit_core_score`. Remove the unreachable block after `lp32_name_ending_at`'s `return None`
- In: a unit test that scores a reserve name (II / B / U21) without raising
- Out: new join recipe. T087 GK Progress. www. Committing `*.fm`. Live `games/*.fm`

## Blind (non-negotiable)

- Do **not** git add `data/saves/` or `*.fm`. Do **not** mmap live `games/*.fm`
- Do **not** add save-named constants

## Acceptance criteria

- [x] `python -c "from ii_squad_discovery import match_reserve_name_score"` works
- [x] Extract no longer NameErrors on `match_reserve_name_score` (unittest on the scorer + existing T084 tests)
- [x] One git commit `T090: …` on FMT/ — no `.fm` in the commit

## Notes / pointers

```
# scripts/ii_squad_discovery.py ~168 (dead, after return None):
    suf = _reserve_suffix(name)
    if suf is None:
        return 0
    core = name[: -len(suf)].rstrip()
    return match_unit_core_score(parent_short, core)
```

Call site: `discover_ii_club_id` ~259. Do not invent a third scoring model.

## Progress

Shipped: `match_reserve_name_score(parent_short, name)` in `scripts/ii_squad_discovery.py` using `_reserve_suffix` + `match_unit_core_score`. Removed the unreachable block after `lp32_name_ending_at`'s `return None`. Join recipe unchanged (`discover_ii_club_id` still scores then `score < 70`).

Verified: `python -c "from ii_squad_discovery import match_reserve_name_score"` from `scripts/` (Sample Town II → 100). `python -m unittest tests.test_match_reserve_name_score_t090 tests.test_unit_squads_t084` — 11 tests OK. No `.fm`.
