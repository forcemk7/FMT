---
id: T072
title: One extract Python at a time; kill leftovers
status: done
priority: 1
owner: worker
claimed_at: 2026-08-15T11:33:00+02:00
started_at: 2026-08-15T11:34:00+02:00
completed_at: 2026-08-15T11:39:00+02:00
depends_on: []
---

# T072 — Starting the app must not spawn 5×2GB Python extracts

## Why

User opens FMT to check HA. Startup runs several `extract-first-team-fast.py` at once (reload / poll / no server lock). Each decompresses the career save to ~2GB. Machine commit explodes; they cannot use the table.

## Scope

- In: At most **one** extract Python. New request waits or reuses the lock. Client disconnect / Vite restart kills that child (Windows `taskkill /T`). Stale pid from a previous `npm run dev` is killed on server start
- In: First-team and favoured-scout share that lock (sequential, not parallel)
- Out: Faster decompress. Dynamics. Suggest. T069 commit

## Acceptance criteria

- [x] Two overlapping `/api/roster/first-team` GETs do not run two Pythons at once
- [x] Abort/disconnect kills the extract child
- [x] Vite server start kills a leftover extract pid
- [x] Live `games/*.fm` still refused; `(v02)` still not copied

## Notes / pointers

- `extractFirstTeam` / `extractFavouredClubScouts` spawn with no AbortSignal
- `vite.config.ts` `runExtractStreaming` has no mutex (`ingestInFlight` is copy-only)
- `data/saves` may hold König + dynamics-a/b/c — do not extract those in parallel

## Progress

Shipped: `createExtractGate` serializes roster/scout extracts. Spawn records `tmp/fmt-extract.pid`; Vite start `taskkill /T` leftovers; request `close` aborts and kills the child. First-team and favoured-scout share the lock.

Verified: `npx vitest run tests/extract-gate.test.ts tests/save-paths.test.ts` (14 passed). Live path still refused. Restart `npm run dev`. Kill leftover `python.exe` from the previous burn once in Task Manager if RAM is still high. One extract still ~2GB while it runs, then idle.
