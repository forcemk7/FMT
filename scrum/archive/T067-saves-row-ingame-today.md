---
id: T067
title: Sync idle when caught up; in-game today must move
status: done
priority: 1
owner: worker
claimed_at: 2026-08-15T01:41:00+02:00
started_at: 2026-08-15T01:43:00+02:00
completed_at: 2026-08-15T02:01:00+02:00
depends_on: [T064, T065]
---

# T067 — Daily SI write → copy → extract → In-game today; Syncing is not idle

## Why

User loop: FM saves (daily in-game) → FMT hears the live `games/*.fm` mtime → copy `data/saves` → extract → Manage Saves **In-game today** is FM’s calendar today.

What they see: **Updated · 2040-01-13 · 36 players**, Uploaded Aug 15 01:34, In-game **Jan 13, 2040**, strip stuck on **Syncing**. July is gone; the date still does not follow in-game today. Syncing never going idle means they cannot tell copy/extract from a hang. T063 residual: `today_ptr` is sparse — Jan 13 can freeze while they play Jan 14+.

## Scope

- In: Live SI `games/` **stat/watch only** → settle → copy selected basename into `data/saves` → extract the copy → persist `gameDate` + `extractedAt` on the active row. Never extract the live file. No `(v02)` / other clubs
- In: Extract `gameDate` is **in-game today** (moves when they save a new calendar day). Not filename. Not the July cluster. Not a frozen `today_ptr_latest` if a later calendar today exists in the blob
- In: **Syncing** only while copy/settle/extract is actually running. When caught up: clear Syncing; flash **Updated · {gameDate}** then the trust line. 8s poll / queued SSE must not start another extract if dest already matches the last persist
- Out: New Saves picker. Progress chart. Inventing a pack strip. Suggest. Extract speed rewrite / matching NG Regens (different job: face-pack install, not HA extract). ROADMAP unfunded

## Acceptance criteria

- [x] After a finished extract: strip is not stuck on Syncing; row Uploaded is that run; In-game today is extract `gameDate`
- [x] Two live writes, in-game dates D1 then D2: second extract’s `gameDate` is D2; row shows D2 (König daily save — not stuck on 2040-01-13 if FM today is later)
- [x] Same in-game day re-save: may recopy; In-game today unchanged; Syncing ends
- [x] Caught-up idle: poll does not re-extract; strip is not Syncing
- [x] Live path still refused for extract; `(v02)` not copied

## Notes / pointers

- Row already shows In-game / Uploaded (`syncRosterSavesMenu`). Display is not the gap
- `setRosterSyncStatus` always paints **Syncing** (detail is tooltip only). `refreshSaveFromDisk` + 8s poll `waitForSettle` default true + `rosterBackgroundSyncQueued` can chain extracts on a 690MB file
- `discover_game_date` / `today_ptr_latest` in `scripts/extract-first-team-fast.py` — T063 residual. Prefer a marker that advances on a new in-game day (e.g. current calendar-run end) without returning to 2039-07-25
- `destCoversLiveSnapshot` / `shouldRefreshRosterFromDisk` — recopy must not imply infinite extract
- Tests: `tests/test_game_date_t063.py`, `tests/save-paths.test.ts`

## Progress

Stuck Syncing: 8s poll defaulted `waitForSettle: true` on the **dest copy** (already settled server-side) and `shouldRefreshRosterFromDisk` retriggered on 1ms mtime jitter / dest.mtime vs `extractedAt`. Queued SSE then chained another 690MB extract.

Stuck date: `today_ptr` is sparse (König dest still 2040-01-13). Later prelude dates (Jan 22, Feb 5, 2043) are fixtures, not today. Walk consecutive prelude days **after** latest today_ptr (calendar-run end). Gapped fixtures do not jump.

Shipped:
- `destMatchesLastPersist` + persist `diskSize`; poll/queue skip extract when dest is the last persist snapshot; leftover Syncing cleared
- Client settle default **false** (server already waited on live before copy)
- `discover_game_date`: today_ptr_latest, then consecutive prelude run end

Verified: `python -m unittest tests.test_game_date_t063 -v` (7 ok); `npx vitest run tests/roster-store-ingest.test.ts tests/save-paths.test.ts` (17 passed). Reload the app (restart `npm run dev` if the extract script is already loaded). Live `games/*.fm` still never extracted.

Residual: König copy at Uploaded 01:34 has no consecutive prelude after 2040-01-13, so In-game today stays Jan 13 until FM writes the next consecutive calendar day (or a later today_ptr). Then re-extract.
