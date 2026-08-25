---
id: T126
title: Restore full-save index on Load Active Save
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-08-25T16:16:00Z
started_at: 2026-08-25T16:16:00Z
completed_at: 2026-08-25T16:18:00Z
depends_on: []
---

# T126 — Restore full-save index on Load Active Save

## Why

Owner uses Live Editor for world reach. Managed-squad-only load was a speed shortcut; they want original GlassScout behaviour: **load everything**.

## Scope

- In: `load_active_save` runs full player database index (`collect_snapshot(true, …)`), same as original GlassScout path
- In: Progress stages still emit; honest partial if index fails
- Out: UI redesign, performance tuning beyond restoring the flag

## Acceptance criteria

- [x] After Load Active Save with FM open, `databaseScope` is `full-save-index` (or honest partial + warning)
- [x] Indexed/search players beyond the managed 35 are available again
- [x] Managed squad still loads (not replaced by empty)

## Progress

Reverted `load_active_save` to `collect_snapshot(true, …)`. Startup already shows “Indexing wider player database…”.
