---
id: T065
title: Auto-sync idle when data/saves copy is missing
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-14T21:43:00Z
started_at: 2026-08-14T21:44:00Z
completed_at: 2026-08-14T21:50:00Z
depends_on: [T056]
---

# T065 — Copy the active Career Save even if data/saves has no file yet

## Why

FM saved König **less than 2 minutes ago**. FMT still shows 97/99 from the last browser extract. `data/saves` has **no** `FC Schalke 04 - Bastian König - FM24Career.fm` (only dynamics-a/b). T056 watch copies only names that already exist in `data/saves`, so the live write is ignored. Auto-update is idle. HA daily x cannot appear.

## Scope

- In: If the **active** FMT save basename exists in SI `games/` and is missing (or stale) in `data/saves`, copy then extract — same T056 settle/copy rules, still never extract the live file
- In: Watch: same-name live `.fm` may create the dest file (today `resolveFmSaveByName` returns null → no-op)
- Out: Copying every career in `games/` (v02–v10, other clubs). Extracting the live path. Suggest. New Saves picker

## Acceptance criteria

- [x] Live `…FM24Career.fm` written, dest missing: dest appears in `data/saves` and roster extract runs from the copy
- [x] Live `…FM24Career (v02).fm` is not copied
- [x] Extract still throws on a `Sports Interactive/…/games/*.fm` path
- [x] 97/99 after a live save is from that extract (new `extractedAt`), not a stale localStorage roster

## Notes / pointers

- 2026-08-14 23:40: live König `LastWriteTime` 23:40; `data/saves` has no matching `.fm`. Vite log: watch started, no copy. `npm run dev` is running
- `ingestTrackedLiveSave` / `ensureSaveWatch` in `vite.config.ts` — `if (!resolveFmSaveByName(key)) return`
- Client poll `fetchSaveDiskStat(active)` 404s when dest is missing → `maybeRefreshActiveSaveFromDisk` returns
- T056: selected **or** already-in-`data/saves`. Implementation only did the second
- Tests: `tests/save-paths.test.ts`

## Progress

Shipped: dest-missing copy of the **selected** Career Save (SSE `?save=` + poll `POST /api/roster/pull-live`). Watch no longer requires dest to already exist. `(v02)` / other careers still skipped. Extract still refuses live `games/*.fm`. Verified: `npx vitest run tests/save-paths.test.ts` — 10 passed. Restart `npm run dev`.
