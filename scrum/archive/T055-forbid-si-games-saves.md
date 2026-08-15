---
id: T055
title: Never read live FM games/*.fm — data/saves only
status: done
priority: 1
owner: scrum-master
claimed_at: "2026-08-14T16:40:00+02:00"
started_at: "2026-08-14T16:40:00+02:00"
completed_at: "2026-08-14T16:50:00+02:00"
depends_on: []
---

# T055 — Never open Sports Interactive/games/*.fm

## Why

**Loop break (behavior):** User gets FM GUI “could not save” on autosave. FMT was watching and extracting the **live** Career Save under `Documents/Sports Interactive/Football Manager 26/games/`. Opening that file while FM writes it locks the save.

## Scope

- In: `.fm` resolve / watch / extract = `data/saves` only; refuse SI `games/` paths; agent rule
- Out: SI `graphics/` faces/logos (keep); Suggest; T053 faces; T054 Progress chips

## Acceptance criteria

- [x] `saveSearchDirs` / auto-sync watch do not touch SI `games/`
- [x] Extract rejects a path under `Sports Interactive/.../games/*.fm`
- [x] Copy into `data/saves` still extracts

## Notes / pointers

- `shared/save/save-paths.ts` previously searched SI games **first**
- `vite.config.ts` `ensureSaveWatch()` watched `resolveFmGamesDir()`
- Spikes `scripts/spike-fm-container.py` / `-2.py` opened SI games directly

## Progress

Shipped: search/watch/extract only `data/saves`. `assertNotLiveFmGamesSave` on TS extract + Python extractors. Agent rule `.cursor/rules/fm-save-isolation.mdc`. Verified `tests/save-paths.test.ts`. Restart `npm run dev` required so the old SI `fs.watch` dies.
