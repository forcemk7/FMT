---
id: T056
title: Copy selected SI games save into data/saves then extract
status: done
priority: 1
owner: cursor-worker
claimed_at: "2026-08-14T16:55:00+02:00"
started_at: "2026-08-14T16:55:00+02:00"
completed_at: "2026-08-14T17:00:00+02:00"
depends_on: []
---

# T056 — Copy live FM save → data/saves; extract the copy only

## Why

T055 stopped FMT opening `Sports Interactive/…/games/*.fm` because that locked FM autosave. Alignment with the latest in-game save is still the load step. **Allowed surface:** after FM finishes writing, **copy** the selected Career Save into `data/saves`, close the live file, **then** extract the copy.

## Scope

- In: watch SI `games/` with **dir events + stat only**; when the **selected** `.fm` (same basename as the active FMT save / existing `data/saves` copy) is stable, copy it to `data/saves`, then existing extract/auto-sync runs on the copy
- In: copy is short-lived and share-friendly; no mmap / no extract / no long-lived handle on the live `.fm`
- Out: extracting or watching-open the live file; copying every career in `games/`; new Saves UI picker; Suggest; faces; T054 leftovers

## Acceptance criteria

- [x] Extract still throws if given an SI `games/*.fm` path
- [x] After FM writes the selected save and it settles, `data/saves/<same-name>.fm` is a newer copy and the roster extract runs from that path
- [x] Live file is not held open during extract (copy finishes first)
- [x] Untracked names in `games/` are not copied (selected / already-in-`data/saves` only)
- [x] FM can autosave while FMT is running (no exclusive lock of the live `.fm`)

## Notes / pointers

- Restore `resolveFmGamesDir()` for **watch + copy source only** — not `saveSearchDirs` / extract
- `waitForFileStable` must be allowed on the live path (**stat only**). Today `assertNotLiveFmGamesSave` is wired into it — split: assert is for extract, not for settle/copy
- `vite.config.ts` `ensureSaveWatch()` currently watches `data/saves` only (T055). Watch SI `games/` again; on stable write → copy → then notify `save-changed`
- Client already ignores SSE unless `saveName` matches `activeSaveName` (`startSaveAutoSync` in `web/main.ts`)
- Keep the 8s poll on **`data/saves` only** — do not poll-open the live file
- Windows: copy may EBUSY if FM still writing — retry after settle; do not loop-open during the write
- Tests: live path refused by extract; copy helper writes into `data/saves`; `saveSearchDirs` still repo-only

## Progress

Shipped: SI `games/` dir-watch + stat settle + stream-copy of **tracked** names (already in `data/saves`) into that copy; then SSE `save-changed` so extract runs on the copy. Extract still asserts live path. Untracked `games/*.fm` ignored. `npx vitest run tests/save-paths.test.ts` — 8 passed. Restart `npm run dev`.
