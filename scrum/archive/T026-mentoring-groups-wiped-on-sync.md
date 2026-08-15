---
id: T026
title: INCIDENT — stop extract refresh wiping mentoring groups
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-13T12:30:00+02:00
started_at: 2026-08-13T12:30:00+02:00
completed_at: 2026-08-13T12:33:00+02:00
depends_on: []
---

# T026 — INCIDENT: mentoring groups wiped on extract / refresh

## Why

**Loop break (behavior):** User reports mentoring groups **keep getting wiped** — UI shows "No mentoring groups yet" after sync/re-extract despite prior work. Livelihood loop loses configured groups + manual Dynamics labels.

**Likely cause (code review):**
1. `pruneMentoringGroups()` drops groups when member UIDs ∉ current roster, then **`saveMentoringStackToStorage()` persists the empty list**.
2. On load, if `store[saveName].groups === []` exists, **legacy compound-key migration is skipped** — recovery from older keys blocked forever.
3. Extract refresh changes `extractedAt` → session rebuild → prune runs; partial roster / uid mismatch / transient empty roster can zero groups permanently.

## Scope

- In: **never persist** a prune that would delete all groups when storage previously had groups for that save (fail closed; log warning)
- In: on load, if direct key has empty `groups`, still attempt **legacy prefix migration** (`${saveName}|…`)
- In: skip prune-and-save when roster identity is incomplete (e.g. `clubAllPlayers().length === 0` or FT count below trust threshold)
- In: regression test: simulate extract refresh with stable UIDs → groups survive; simulate partial roster → groups not persisted away
- Out: T025 Suggest logic; Dynamics RE; subunit null wipe (T023 — reopen separately if II/U19 melt returns)

## Acceptance criteria

- [x] Re-extract / disk sync with stable squad does **not** clear persisted mentoring groups
- [x] Partial / failed extract cannot persist empty groups over a non-empty saved stack
- [x] Empty direct key still migrates from legacy compound keys when available
- [x] Test locks at least one wipe scenario above
- [ ] User smoke: build 1+ groups → trigger sync → groups still visible

## Notes / pointers

- `web/main.ts`: `pruneMentoringGroups`, `loadMentoringStackFromStorage`, `saveMentoringStackToStorage`, `ensureMentoringCacheForRoster`
- Storage key: `fmt-mentoring-stack-v2`, persist key = save file name
- User sees "84/85 mentoring-ready" — roster mostly fine; wipe is persistence/prune, not empty FT tab

## Progress

- Extracted `web/mentoring-stack.ts`: load (legacy migration when direct key empty), prune decision (fail-closed wipe-all, skip incomplete roster), persist guard.
- Wired `web/main.ts`: `pruneMentoringGroups` uses `decideMentoringPrune`; `saveMentoringStackToStorage` uses `canPersistMentoringGroupsToStore`.
- Added `tests/mentoring-stack.test.ts` — 10 tests covering legacy migration, stable-UID survival, partial roster skip, wipe-all fail-closed, persist guard.
- Verified: `npm test -- tests/mentoring-stack.test.ts` — 10/10 pass.
