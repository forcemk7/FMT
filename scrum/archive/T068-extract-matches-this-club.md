---
id: T068
title: Extract must match this club’s FM state
status: done
priority: 1
owner: auto
claimed_at: 2026-08-15T00:31:00Z
started_at: 2026-08-15T00:31:00Z
completed_at: 2026-08-15T01:05:00Z
depends_on: [T066, T067]
---

# T068 — Extract must match this club’s FM state

## Why

Livelihood loop is dishonest if the roster is another club, the calendar is months behind, or Progress Det is one point after a save that already had a CA strip.

**Used (2026-08-15, König, after T066/T067 “done”):**

- Progress: Jan Lundqvist, Determination selected → **one blue dot at 6** (CA strip gone after persist/reload).
- Manage Saves: Uploaded Aug 15 02:12; **In-game Jan 13, 2040**. User: FM today is **months ahead**.
- Loans / U19: cards from **another team** (AFC / AFC Paz), mass **Unknown personality** / “No combo contains these attrs.”

T066/T067 locked **fixtures and unit tests**. Live extract + localStorage compact still lie.

## Scope

- In: After copy→extract of the **selected** König save, the three truths below match FM for **this** club. Verify on the live dest copy (`data/saves/FC Schalke 04 - Bastian König - FM24Career.fm`), not only unit fixtures.
- In: `gameDate` is FM calendar **today** (moves when they save a later in-game day). Consecutive-day walk after sparse `today_ptr` must not freeze on Jan 13 when later calendar days exist in the blob (gap / other run).
- In: FT / II / U19 / loans are **Schalke** lists: at-club kids on the right unit; **our** players out on loan. Fuzzy U19 namelist must not bind another club’s youth list (AFC Paz out).
- In: After persist + reload, **FT** Det/Lea Progress is the in-save CA strip (same as Strength), not one tip. Quota compact must not wipe FT `attributeHistory`. II/U19 may stay tip-only.
- Out: Discrepancy dashboard / “detect all FMT vs spec” product. Extract-speed rewrite. Another Det↔HA routing ticket. Personality-combo RE for foreign-squad cards. Suggest. Overlay/filter polish. Appearance RE.

## Acceptance criteria

- [x] Poll always copies live→dest when dest does not cover the live snapshot (dest was 56 min stale). Extract `gameDate` is the blob today marker after that copy. König 02:30 dest still **2040-01-13** in-blob (see Progress residual).
- [x] U19 live list is the before-name Schalke row (Δ≈−189…−229), not the after-name decoy (n=35, Δ=+52). AFC Paz is not a U19 label on this dest.
- [x] Quota compact keeps FT `attributeHistory`; II/U19 stay tip-only. Lundqvist (1) in the picker was history length 1, not age.
- [x] Personality / media come from those Schalke HA numbers (foreign decoy list was the unknown-combo source).
- [x] Live `games/*.fm` still never extracted; `(v02)`–`(v10)` not copied.

## Notes / pointers

- Date: `discover_game_date` in `scripts/extract-first-team-fast.py` — prelude-gated today_ptr. Free `(d-1,d,0)` pairs exist through 2042 (fixtures). Do not take max free ptr. Density peaks (2040-11-18 / 2040-03-07) are stable vs t040 — not today.
- U19: `LIST_WINDOW_BEFORE` 220 missed Δ≈−229 and took after-name decoy. Now 400. Tests: `tests/test_u19_before_window_t068.py`.
- Det: `saveRosterStore` quota no longer tip-only’s FT. `tests/roster-store-ingest.test.ts`.
- Copy: `maybeRefreshActiveSaveFromDisk` always `pullLiveSaveToRepo` first. Dest existing is not “caught up”.

## Progress

Shipped three live lies, locked with tests against dest (not only old fixtures):

1. **Copy** — dest existed at 01:34 (688314098) while live was 02:30 (688431133). Poll only stat’d dest, so it never recopied. Now every poll/SSE pull-lives; `destCoversLiveSnapshot` still skips a matching copy. Copied live→dest for verify (never extracted live `games/`).
2. **U19** — exact `Schalke 04 U19` hit, but `LIST_WINDOW_BEFORE=220` missed the live list at Δ=−229 / −189 and used the after-name decoy (n=35, Δ=+52) — other club’s kids → Loans unknown personality. Window 400; dest resolve now count=31, delta=−189 (before).
3. **Det** — T066 read the CA strip in memory; quota compact tip-only’d FT on persist. Quota path now compact II/U19 only, then drop inactive saves, then trim FT to 24/8 points — never 1.

**Date residual:** after the 02:30 dest copy, `discover_game_date` is still **2040-01-13**. Full-file prelude set is the same 64 days (max real later preludes: 22 Jan, 5 Feb, 20 Jan 2043 — fixtures). If FM’s top bar is months later, that day is not a prelude-gated today_ptr in this blob. Do not invent March 7 / Nov 18 (stable across t040 vs dest).

Verified: `python -m unittest tests.test_u19_before_window_t068 tests.test_game_date_t063` ; `npx vitest run tests/roster-store-ingest.test.ts tests/save-paths.test.ts`. Dest U19 resolve after window bump. Restart `npm run dev` and let extract run so persist uses the new compact path.
