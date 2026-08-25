---
id: T130
title: LE-speed load — drop RAM world scan; fix attr plot loop
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-25T16:30:00Z
started_at: 2026-08-25T16:30:00Z
completed_at: 2026-08-25T16:40:00Z
depends_on: []
---

# T130 — LE-speed load — drop RAM world scan; fix attr plot loop

## Why

Background full private-memory index still crushed the machine vs Live Editor (~2s). Search already prefers FM Dossier SQLite. Attribute history panel infinite-looped (`Maximum update depth exceeded`).

## Scope

- In: Remove automatic multi-GB RAM world scan from load path; world reach via Dossier
- In: Fix AttributeHistoryPanel setState/useEffect loop
- Out: Matching LE’s internal indexer (unknown); installer

## Acceptance criteria

- [x] Load does not start a full private-memory player scan
- [x] Attribute history tab does not throw max update depth
- [x] World search still works when Dossier index is present

## Progress

- `load_active_save` → squad-only `collect_snapshot(false)`; no background scan thread
- History panel: no syncing useEffect; defaults via `active === null`
