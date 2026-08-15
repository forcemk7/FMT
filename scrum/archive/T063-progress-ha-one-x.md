---
id: T063
title: Progress HA plot stays one x after daily syncs
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T061]
---

# T063 — Daily extracts must add HA x; Det/Lea must not collapse

## Why

User: in-game calendar has moved a long time with a **daily rolling Career Save** and T056 syncs. Progress HA is still one vertical column for everyone (Seimen, Kizza, **Yoan Robert**). Yoan changed personality **and** media handling — pack numbers moved — still no line. Det/Lea also sit on that single x (T061 pulled them off the CA strip). Strength can show −1 on the same screen. The “see HA shift after mentoring” loop is dead.

## Scope

- In: Find why `fmt.ha-history.v1` has one snapshot per player despite many extracts. Likely: extract `gameDate` does not move (upsert same key) or the store is not kept across reload. Fix so each **new in-game date** appends a point
- In: Distinct dates stay even when pack values are unchanged (already tested). Yoan-class value changes must be a second x + chip delta
- In: Det/Lea: do not collapse to one tip. If HA store has ≥2 dates, plot that series. If it has 1 date and FT CA strip has Det/Lea history, use the strip so they are not worse than Strength
- Out: Inventing an in-save pack strip. Full II/U19 CA history (quota). New charts. Suggest. Rebuilding the pane. T062

## Acceptance criteria

- [x] Two T056 extracts, in-game dates D1 then D2: Kizza/Seimen pack series length **2**; plot is a line (not one column)
- [x] Same in-game date re-extract: series length unchanged (replace that day)
- [x] Unchanged pack values still keep both dates (two x, empty delta on those chips)
- [x] Yoan (personality + media changed): at least one pack chip has a non-empty All-time delta; plot has ≥2 x
- [x] Det/Lea are not a single x when FT CA strip has ≥2 Det points **or** HA store has ≥2 dates
- [x] II/U19 with no CA strip still follow HA store only (no quota blow-up)

## Notes / pointers

- `upsertHaSnapshot` in `web/ha-history-store.ts` — same `gameDate` replaces. Copy into `data/saves` keeps a **fixed filename** (no `In-game date DD.MM.YYYY`). `discover_game_date` / `parse_save_game_date_hint` in `scripts/extract-first-team-fast.py` — `calendar_run_start` is season start; filename hint is treated as ground truth
- `mergeHaHistoryFromRoster` on persist in `web/main.ts`; `backfillHaHistoryFromRosterStore` on every `applyActiveRosterFromStore` reload (roster itself only has the latest extract)
- T061: `historyForAttrId` / `isHaProgressAttrId` — Det/Lea no longer read `attributeHistory`
- Proof players: Yoan Robert (II/U19), Dennis Seimen, Sam Kizza
- Tests: `tests/ha-history-store.test.ts`; add extract-date coverage if the date is stuck

## Progress

Stuck date: T056 copies keep a fixed filename, so there is no `In-game date DD.MM.YYYY` hint. `discover_game_date` then used `today_ptr_dense_window`, which locked to the pre-season cluster **2039-07-25** while later sparse ptrs (Nov/Dec/Jan) existed. Every extract upserted the same HA key → one vertical column.

Shipped:
- No filename hint → latest `today_ptr` (`today_ptr_latest`). Filename hint still ground truth.
- Koenig decomp: 2039-07-25 → **2040-01-13**.
- Det/Lea: HA store ≥2 dates stays on snapshots; 1 date + FT CA strip ≥2 Det points uses the strip. II/U19 tip-only stays on HA store.

Verified: `python -m unittest tests.test_game_date_t063 tests.test_live_ca_continuity -v` (12 ok); `npx vitest run tests/attribute-evolution.test.ts tests/ha-history-store.test.ts` (25 passed).

Residual: today_ptr is not every in-game day (sparse markers). A new HA x appears when that marker moves, not necessarily on each FM calendar day. Existing `2039-07-25` localStorage points remain; next T056 extract with a later date appends the second x. Restart not required for extract; reload the app after extract to see Progress.
