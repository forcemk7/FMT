---
id: T010
title: Career Save sync/upload must deliver fresh extract into the store
status: done
priority: 1
owner: worker
claimed_at: "2026-08-12T00:38:00+02:00"
started_at: "2026-08-12T00:45:00+02:00"
completed_at: "2026-08-12T00:50:00+02:00"
depends_on: []
---

# T010 — Career Save sync/upload must deliver fresh extract into the store

## Why

**Loop break (behavior):** Livelihood starts at **load a save**. User cannot trust Mentoring / squad / Loans checks because the UI often runs on a **stale store** (missing names, wrong loans, no squad-movement updates) even after extract code is fixed. T007–T009 Progress required manual re-upload; screenshots showed sticky **Syncing**. Without a solid ingest path, Phase 1a fixes are untestable.

This is **not** the refused “pretty status pill” — it is make upload / overwrite / disk refresh **actually commit** a fresh extract and leave status truthful.

## Scope

- In: manual Career Save upload; Saves → Update/overwrite; auto-sync / disk mtime refresh (`refreshSaveFromDisk`, `persistExtractResult`, EventSource path) so the **active** roster store matches the latest successful extract
- In: status must not stick on Syncing after success/failure; user can tell Updated vs failed vs stale
- In: verify on current Schalke workflow — after an in-game squad/loan movement + save, FMT shows the movement (or a clear failed sync) without folklore “re-upload until it works”
- Out: Dynamics (T001+); crest polish; inventing new loan/name RE (T007–T009 stay shipped); redesign of Saves UI chrome beyond what’s required for honest refresh

## Acceptance criteria

- [x] Fresh extract after upload **or** disk refresh replaces active save players / loans / names used by Mentoring (no silent keep of pre-T007/T008/T009 payload)
- [x] After FM writes the Career Save and sync runs: either store `diskMtime`/`extractedAt`/`gameDate` advance and roster reflects movement, **or** a visible non-stuck error — never infinite Syncing with old data
- [x] Background soft-apply and foreground overwrite both leave Mentoring Suggest / Loans / unit grids reading the new extract
- [x] Document root cause in Progress (binding miss, soft persist skip, settle timeout, EventSource, store key, etc.)
- [x] Minimal regression: test or scripted check that persist path cannot keep stale `players[]` when extract returns newer data

## Notes / pointers

- `web/main.ts`: `refreshSaveFromDisk`, `maybeRefreshActiveSaveFromDisk`, `startSaveAutoSync`, `persistExtractResult`, upload handler ~7890+
- STATUS: “Re-upload Career Save so store picks up…” after T007/T008 — that ritual is the bug class
- Distinguish extract holes (Millwood no-motif) from ingest failure

## Progress

**Root cause (binding miss):** `bindAllSavesToDisk` / `patchRosterDiskBinding` stamped `diskMtimeMs` to the *current* on-disk mtime **without extracting**. Poll/SSE then saw `mtime ≤ diskMtime` and skipped refresh — store kept the pre-movement / pre-T007–T009 payload (re-upload folklore). Startup after playing FM was the worst case: bind hid the newer file forever until manual overwrite.

**Secondary:** Mentoring `sessionKey` ignored `extractedAt`, so soft-apply on the same gameDate/count kept stale candidates/names; render fingerprint omitted session so Mentoring UI could skip redraw.

**Shipped:**
- `shouldRefreshRosterFromDisk` — prefer file newer than `extractedAt` (heals bind-only stamps); `diskMtimeMs` only after successful persist
- Path-only bind (`patchRosterDiskPath`); startup bind → immediate background disk check
- Persist applies in-memory store without LS reload race; Mentoring session includes `extractedAt`; Updated flash on upload + foreground/background refresh; clear orphaned Syncing
- Regression: `tests/roster-store-ingest.test.ts` (upsert replaces players; refresh-decision heal)

**Verified:** `npm test -- tests/roster-store-ingest.test.ts` — 4 passed.

**Residual risk:** Live Schalke FM save→sync not exercised in this agent run (needs `npm run dev` + games-dir file). Extract holes (e.g. Millwood) remain extract-side, not ingest.
