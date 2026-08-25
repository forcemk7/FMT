---
id: T134
title: Stock GlassScout load parity on native saves
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-25
started_at: 2026-08-25
completed_at: 2026-08-25
depends_on: []
---

# T134 — Stock GlassScout load parity

## Why

Stock GS indexes ~16k on native FM26. FMT often ended at ~34 with a silent world-index fallback. Owner wants FMT load to behave like stock first.

## Acceptance

1. `load_active_save` uses `collect_snapshot(true)` (full private-memory index).
2. Executable identity always SHA-256 hashes like stock (no version-only map shortcut).
3. Entity map match requires fileVersion + productVersion + sha256 + arch like stock.
4. If world index fails, surface the **real** error in snapshot warnings/`dataError` (no silent club-only success that looks “fine”).
5. Warnings do not claim Dossier is the primary world path when the memory index ran.

## Out of scope

- Multi-manager / continue saves (T135)
- Speed / 400k continue indexing strategy
- Tactics formation validation

## Progress

- Restored always-hash + exact entity-map match (stock).
- World index errors → `database_index_status=failed`, `dataError`, explicit warning.
- Dossier no longer masks a failed memory index as “ready/full-save”.
- Warnings describe memory index as the stock path.
- `cargo check --lib` OK.
- Commit: see git log T134/T135.
