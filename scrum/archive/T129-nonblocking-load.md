---
id: T129
title: Non-blocking load — squad first, index in background
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-25T16:20:00Z
started_at: 2026-08-25T16:20:00Z
completed_at: 2026-08-25T16:30:00Z
depends_on: []
---

# T129 — Non-blocking load — squad first, index in background

## Why

After T126, Load Active Save freezes FMT (“Not Responding”). LE feels ~2s interactive. Cause: synchronous full private-memory player scan (up to ~8GB) on the load invoke.

## Scope

- In: Return managed-squad snapshot quickly so the shell stays responsive
- In: Run full-save index on a background thread; emit progress / ready; search works when index completes
- Out: Rewriting the scanner algorithm, installer, UI chrome

## Acceptance criteria

- [x] Load Active Save does not put the window into Not Responding for normal club sizes
- [x] User can open club players / attributes desk while wider index may still be running
- [x] When index finishes, `databaseScope` / indexed counts update; search uses the index
- [x] If background index fails: honest warning; managed squad still usable

## Progress

- `load_active_save` → `collect_snapshot(false)` then spawn `fmt-full-index` thread for `collect_snapshot(true)`
- Emits `fmt-index-ready`; UI merges indexed counts into status
- Warning while background index runs
