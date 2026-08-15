---
id: T058
title: Extract roster faces into data/faces; serve copies
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: []
---

# T058 — Extract faces once into `data/faces` (save-sync shape)

## Why

**Loop break:** Mentoring identity scan still shows initials after T053. Live SI `graphics/` resolve on every `/api/faces/:uid` is the save-lock class of problem: huge packs, slow XML index, request loses the race. Saves already **copy then extract**. Faces need the same: copy once into the repo, then serve the copy.

## Scope

- In: copy roster portraits (FT + II + U19 UIDs) from SI graphics into `data/faces/{uid}.*`; `/api/faces/:uid` serves **only** those files
- In: copy on extract (missing UIDs) and on cache-miss GET; skip if the file already exists
- Out: copying the whole megapack; logos; new face pipeline/UI; Suggest; Sortitoutsi download

## Acceptance criteria

- [x] `GET /api/faces/:uid` reads `data/faces/{uid}.*` when present — does not stream the live pack file
- [x] After a First Team extract, seated roster UIDs with a pack file are copied into `data/faces` (Seimen + at least one regen miss class)
- [x] Confirmed miss (no pack file, no cache) still 404 → initial fallback
- [x] `data/faces/` is gitignored (binaries, like `data/saves/`)

## Notes / pointers

- Mirror T056: SI graphics = copy **source**; FMT reads `data/faces`
- `shared/faces/face-index.ts` stays the resolver for the copy step
- Do not parse XML on a cache hit
- Mentoring `bindPlayerFace` unchanged

## Progress

- Shipped: `shared/faces/face-cache.ts` — `data/faces/{uid}.*`. `/api/faces/:uid` serves the copy only; cache-miss copies from SI then serves. First Team extract copies missing FT+II+U19 UIDs in the background. Skip if file exists.
- Verified: `npx vitest run tests/face-cache.test.ts tests/face-index.test.ts` (3 passed). `data/faces` has Seimen `2000175080.png` and regen class Kizza/Itu/Yoan.
- Residual: restart `npm run dev` so the faces plugin serves `data/faces`. First regen miss after an empty cache waits on the SI index once, then sticks.
