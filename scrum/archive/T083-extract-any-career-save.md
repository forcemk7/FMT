---
id: T083
title: Managed club identity from any Career Save
status: done
priority: 1
owner: worker
claimed_at: 2026-08-16T03:00:00+02:00
started_at: 2026-08-16T03:00:00+02:00
completed_at: 2026-08-16T03:20:00+02:00
depends_on: []
---

# T083 — Managed club identity from any Career Save

## Why

Cloud = whoever uploaded. Step 1 of the extract (ROADMAP §6). If this is wrong, every later join is the wrong club or empty. The development Career is a smoke check if a `.fm` happens to be local — **not** the model.

## Scope

- In: `scripts/extract-managed-team.py` + the same `discover_managed_club` / catalog path used by `extract-first-team-fast.py`. Structural tag → manager lp32 → club short → club UniqueID
- In: prove the parser on a **synthetic identity blob** (construct the tag + lp32s + u32). Optional smoke: any untracked `data/saves/*.fm` already on disk
- Out: FT/II/U19 lists (T084). HA/CA (T085). Loans (T086). New club-id / name / MB / offset constants from any real save. Editing `.fm`. Live `games/*.fm`. Committing `data/saves/` or `*.fm`

## Blind (non-negotiable)

- Do **not** git add `data/saves/`, `*.fm`, faces, logos, `.env`
- Do **not** mmap `Documents/Sports Interactive/…/games/*.fm`
- Do **not** wait for a second Career Save. Do **not** set blocked for “need another .fm”
- Do **not** put a real club name, manager name, UniqueID, or file offset from a local `.fm` into source, fixtures, comments, or ticket Progress as law
- If a local `.fm` exists, you may smoke-run it and tell the human the printed identity. That run is not the recipe

## Acceptance criteria

- [x] Parser is covered by a synthetic blob test (tag `00 95 0e 01` and `00 95 0e 02` → person → club short → UniqueID)
- [x] `EARLY_SCAN` / `IDENTITY_DEADLINE` are search bounds, not a second save’s byte as law. If the tag can sit later, search continues; fail = diagnostic (tag/offset/bytes scanned), not a silent wrong club
- [x] No new save-named constants in the identity path
- [x] One git commit `T083: …` on FMT/ — no `.fm` in the commit

## Notes / pointers

- Recipe: `00 95 0e 01|02` → person → club short → u32 (`extract-managed-team.py`)
- Next: T084 (unit lists). Do not start T084 in this commit

## Progress

Shipped: identity parser is tag → person lp32 → club short lp32 → UniqueID u32. `extract-first-team-fast.py` uses the same `discover_managed_club`. `EARLY_SCAN` / `IDENTITY_DEADLINE` are expanding search bounds; a tag past the deadline still parses. Miss returns tag hexes, last tag offset, and bytes scanned — not a guessed club.

Verified: `python -m unittest tests.test_managed_club_identity_t083 tests.test_world_lists_skip_t076` (synthetic blob, both tags, later-than-deadline continue, miss diagnostics). Optional smoke on local `data/saves/*.fm` is not the recipe and is not committed.

Next: T084 (unit lists). Not started.
