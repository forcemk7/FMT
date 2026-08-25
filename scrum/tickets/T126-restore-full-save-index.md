---
id: T126
title: Restore full-save index on Load Active Save
status: ready
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
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

- [ ] After Load Active Save with FM open, `databaseScope` is `full-save-index` (or honest partial + warning)
- [ ] Indexed/search players beyond the managed 35 are available again
- [ ] Managed squad still loads (not replaced by empty)

## Progress

_(worker fills)_
