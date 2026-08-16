---
id: T106
title: Continue FM24 gameDate — lock from rolling stack
status: done
priority: 1
owner: composer
claimed_at: 2026-08-16T19:30:00+02:00
started_at: 2026-08-16T19:31:00+02:00
completed_at: 2026-08-16T19:50:00+02:00
depends_on: [T101]
---

# T106 — Continue FM24 gameDate — lock from rolling stack

## Why

T101 continue calendar needs a `today_ptr`. Real FM24 continue has prelude-only hits → `Game Date: —`. Owner will not dictate the FM date. Same club, many in-game days: use the 10-rolling continue stack to **diff** and lock the date blob (T099 method, not club hunting).

## Local inputs (gitignored — do not commit)

Under `data/saves/`:

- `FC Schalke 04 - Bastian König - FM24Career.fm`
- `FC Schalke 04 - Bastian König - FM24Career (v02).fm` … `(v10).fm`

All tag `00950e02`, club 920. Dates differ across the stack. `dynamics-c.fm` is optional extra; prefer this stack.

## Scope

- In: Diff identity / early calendar neighborhoods across the stack. Find the field that **moves with in-game day** and is stable per save. Lock that recipe for tag `02` only
- In: Do **not** use UniqueID-tail (T099). Do **not** take max `c708` prelude / calendar-run end as today (T096)
- In: Synthetic unit tests that encode the locked layout (no `.fm` in git)
- In: + / Update persist `gameDate` so cards and header stop showing `—` on continue
- In: **After** the recipe is locked and tests pass: **delete** the König `FM24Career*.fm` copies from `data/saves/` (base + v02–v10). Leave other saves alone
- Out: Native tag `01`. Squad extract. Pane chrome. Asking the owner for the date string

## Blind (non-negotiable)

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Do **not** mmap live `games/*.fm`
- Do **not** leave the rolling König copies in `data/saves` after the ticket

## Acceptance criteria

- [x] Tag `02` gameDate locked from stack diffs; synthetic tests pass
- [x] Re-extract of a continue save shows a real date (not `—`); native eight still T099
- [x] König `FM24Career.fm` + `(v02)`…`(v10)` removed from `data/saves/`
- [x] One git commit `T106: …` on FMT/ — no `.fm`

## Notes / pointers

- `pick_continue_calendar_date` / `collect_date_candidates` in `scripts/extract-managed-team.py`
- Dump pattern: `tmp/identity/` (gitignored). Compare candidates that change file-to-file
- Steal: T099 multi-save lock — same day field across saves with known day steps

## Progress

Shipped: tag `02` gameDate is UniqueID trailer — lp32 → u32 0 → u32 0xffffffff → u16 doy + u16 year (same decode as T099, including `raw & 0x1FF`). Not UniqueID+4. Not c708 / today_ptr / calendar-run. Method `continue_uid_trailer_doy_year`. Native tag `01` unchanged (T099).

Locked from König FM24Career + v02–v10 diffs (day steps at trailer; calendar stayed stuck on 2040-01-13). Verified on stack + `dynamics-c.fm` before delete. König `FM24Career*.fm` (base + v02–v10) removed from `data/saves/`. Other saves left.

Verified: `python -m unittest` t106 + t101 + t099 + t097 + t096 (27 ok). Local smoke: base → 2040-10-24, v10 → 2040-10-15, dynamics-c → 2040-06-19. No committed `.fm` / `tmp/`.

Commit: _(filled after git)_

Restart `npm run dev` and + / Update a continue save — Game Date should be a real day, not —. Native cards stay T099.
