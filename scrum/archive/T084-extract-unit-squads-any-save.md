---
id: T084
title: FT II U19 lists from this club on any Career Save
status: done
priority: 1
owner: worker
claimed_at: 2026-08-16T03:28:00+02:00
started_at: 2026-08-16T03:30:00+02:00
completed_at: 2026-08-16T03:55:00+02:00
depends_on: [T083]
---

# T084 — FT II U19 lists from this club on any Career Save

## Why

Step 2: **employed players**. This is why a second upload shows **zero Squad rows** (join-miss empties jobs) and why Mentoring cannot trust the pool. Identity is known; the unit join must come from this club’s team object, not one Career’s megabyte band.

## Scope

- In: `ft_squad_discovery.py`, `ii_squad_discovery.py`, `u19_squad_discovery.py`, and the resolve block in `extract-first-team-fast.py` (~identity → `resolve_ft_squad` / II / U19)
- In: join from **this club’s team object** (catalog PRE_NAME → teamId/dup → job-list). Drop save-fitted **gates**: mid-file MB windows as law (`BODY_LO` 40–100MB, U19 `NAME_BAND` 40–120MB), FT count 15–45 as law, `{short} II` as the only reserves name, `{short} U19` as the only youth name, subunit jobId `50_000–2_000_000` as law
- In: join must succeed from **object shape**, not from one Career’s megabyte band or name string
- Out: HA/CA blobs (T085). Loans (T086). World/staff walk. `pick_tid` fallback when identity is known (still poisons Mentoring). New name-lists / club 920 / UID constants. Editing `.fm`. Committing `*.fm`

## Blind (non-negotiable)

- Do **not** git add `data/saves/` or `*.fm`. Do **not** mmap live `games/*.fm`
- Do **not** wait for / demand another Career Save. Do **not** lock offsets, counts, or names from a local `.fm` into source
- Optional smoke on whatever `data/saves/*.fm` already exists; report method + job counts to the human, do not bake that club into the recipe

## Acceptance criteria

- [x] `find_ft_job_list` / II / U19 no longer treat MB windows, FT count 15–45, `{short} II`, `{short} U19`, or subunit jobId `50_000–2_000_000` as **law**. Join is catalog/team object → job-list
- [x] Identity known + list not found still must not silently pick a foreign `pick_tid` squad. Diagnostic on miss; empty jobs only when the object join actually missed
- [x] II/U19: reserve / youth **unit of this club**. Missing unit in FM (no II) = empty subunit, not a failed extract. Do not require the string `{short} II`
- [x] After-name U19 list remains a decoy (shape: live list before the name). Not a Δ-byte from one save
- [x] One git commit `T084: …` on FMT/ — no `.fm` in the commit

## Notes / pointers

- Empty UI today = `mergeClubWideAtClubPlayers` saw no named at-club rows, usually because `select_managed_ft_jobs` returned `jobs: []` after join-miss
- `find_ft_job_list` only searches `dup` hits between 40MB–100MB and requires 15–45 jobs — small clubs and different decompress layouts miss
- II is `f"{parent_short} II"` only — England U21 / Spain B / no reserves all miss
- U19 live list is before-name (window 400); after-name is decoy. Keep that **shape**, not König’s Δ≈−189 as a constant
- Copy-then-extract if you smoke a local file. Never mmap live `games/*.fm`. Never commit that file

## Progress

Shipped: unit lists join from this club’s team object (catalog PRE_NAME → teamId/dup → job-list). Dropped MB windows, FT 15–45, `{short} II` / `{short} U19` as the only names, and subunit jobId 50k–2M as law. Jobs are plausible in 100–50M; count 1–80. Identity known + miss → `ft-club-squad-join-miss` + `missReason`, never `pick_tid`. Missing reserves/youth unit → empty subunit (`ii-unit-absent` / `u19-unit-absent`), not a failed extract. Youth live list is before-name only; after-name stays a decoy.

Verified: `python -m unittest tests.test_unit_squads_t084 tests.test_u19_before_window_t068 tests.test_managed_club_identity_t083 tests.test_world_lists_skip_t076` (synthetic blob: small-club FT, B/U21 reserves, U18 before-name, after-only decoy, pick_tid refused). Optional smoke on a local decompressed copy: method + job counts reported to the human; not the recipe; not committed.

Next: T085 (HA/CA for listed people). Not started.
