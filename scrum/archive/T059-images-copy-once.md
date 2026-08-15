---
id: T059
title: Images copy once into data/; never re-read SI graphics
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: []
---

# T059 — Fetch images once; serve only repo copies (same class as save lock)

## Why

**Loop break:** In-game portraits/crests hitch the same way live `games/*.fm` locked autosave. T058 still **walks SI `graphics/`** on logo index (server start), `/api/faces/status`, and every `/api/logos/:id`. Cached faces were local; logos and status were not. Fetch each needed file **once**, then FMT must not touch the live pack.

## Scope

- In: `/api/faces/:uid` and `/api/logos/:clubId` serve `data/faces` / `data/logos` only when the copy exists
- In: SI graphics is opened **only** to copy a missing uid/club; skip if the file is already in the repo (including after save extract)
- In: no SI walk on server start or `/api/faces/status` / `/api/logos/status`
- Out: copying whole megapacks; new UI; Suggest

## Acceptance criteria

- [x] Cache hit for a face or logo does not `readdir` / `createReadStream` the SI graphics tree
- [x] Server start does not build the live face or logo index
- [x] Status endpoints report repo cache counts without indexing SI
- [x] Missing copies still 404 / initial fallback; first miss may copy once
- [x] `data/logos/` gitignored like `data/faces/`

## Notes / pointers

- T055/T056/T058 shape: live SI = copy source; FMT reads `data/`
- `vite.config.ts` `void ensureLogoIndex()` on configureServer is the startup walk
- `GET /api/faces/status` currently `await ensureFaceIndex()` — remove that
- Mentoring `bindPlayerFace` / `bindClubLogo` URLs unchanged

## Progress

- Shipped: logos copy into `data/logos/{clubId}.*` (same skip-if-exists as faces). GET face/logo serves repo copy only. Status = cache counts, no SI index. Removed startup `ensureLogoIndex`. Extract copies missing crests (club + loan ids) only when absent.
- Verified: `npx vitest run tests/face-cache.test.ts tests/logo-cache.test.ts tests/face-index.test.ts` — 5 passed.
- Residual: restart `npm run dev`. A **new** uid/club still copies once from SI; after that, save sync with a full cache does not open graphics/.
