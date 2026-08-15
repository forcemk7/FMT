---
id: T064
title: HA gameDate from blob only, never filename
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T063]
---

# T064 — Key Progress HA on in-game date, not filename

## Why

User: filename `In-game date DD.MM.YYYY` is unreliable (stale name, T056 strips it, FM label ≠ calendar). The blob today marker is the date that should key HA snapshots, age, and Manage Saves. T063 still treats a filename hint as ground truth when present — that can stamp the wrong day and collapse or mis-order Progress x.

## Scope

- In: `discover_game_date` ignores filename. Always use the in-save today marker (T063 `today_ptr_latest`, not the July dense cluster)
- In: Stop passing `parse_save_game_date_hint` into discover (or pass `hint=None`). Age + HA upsert keep using extract `gameDate`
- Out: New date RE. Parsing FM UI strings. Inventing a pack strip. Suggest

## Acceptance criteria

- [x] Save named `(In-game date 19.11.2039).fm` whose blob today is later (e.g. 2040-01-13): extract `gameDate` is the **blob** date, not 19.11.2039
- [x] Fixed name `Career.fm` (no date in filename): same blob date as above
- [x] Two blob dates D1 then D2 still append HA x; same blob date re-extract still replaces
- [x] Existing `tests/test_game_date_t063.py` filename-as-ground-truth case is inverted or removed

## Notes / pointers

- `scripts/extract-first-team-fast.py` — `parse_save_game_date_hint` / `discover_game_date(..., hint=)` around extract `game_date_hint`
- T063: no hint → `today_ptr_latest`. With hint → still overrides. Drop that override
- Tests: `tests/test_game_date_t063.py`; HA store tests stay (they already take `gameDate` as given)

## Progress

Extract no longer reads the filename for `gameDate`. `discover_game_date` ignores `hint` (filename dates are stale / T056-stripped). Always latest blob today_ptr, not the July cluster.

Verified: dated `(In-game date 19.11.2039).fm` + blob 2040-01-13 → `2040-01-13`; `Career.fm` same. `python -m unittest tests.test_game_date_t063 tests.test_live_ca_continuity -v` (11 ok); `npx vitest run tests/ha-history-store.test.ts` (8 passed — D1/D2 append, same date replaces).

Residual: today_ptr is still a sparse in-save marker, not every calendar day. Re-extract to pick up blob dates. Parser `parse_save_game_date_hint` remains unused.
