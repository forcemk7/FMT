---
id: T131
title: LE-speed load — cache identity, skip bulk role scoring
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-25T16:45:00Z
started_at: 2026-08-25T16:45:00Z
completed_at: 2026-08-25T17:00:00Z
depends_on: []
---

# T131 — LE-speed load — cache identity, skip bulk role scoring

## Why

Load still embarrassing vs Live Editor (~2s). Sweep found: full SHA-256 of `fm.exe` + PowerShell version spawn every load; full IP/OOP role catalogue scored for every squad player on load.

## Scope

- In: Cache executable identity (path + size + mtime) so SHA-256/version aren’t recomputed every Load
- In: Defer `evaluate_player_roles` off the load path
- In: Cache manager-signature scan hit for the live process/module base within the session
- In: Match entity map on unique fileVersion+arch without hashing fm.exe when unambiguous
- Out: Rewriting memory scanner; full LE parity research

## Acceptance criteria

- [x] Second Load Active Save in the same session does not re-hash all of fm.exe
- [x] Squad load does not run full role-catalogue scoring per player
- [x] CA/PA/HA + attributes still load; club desk usable
- [ ] Owner reports material step toward LE feel (or we profile the next bottleneck)

## Progress

Sweep (solid wins):

1. **Full-file SHA-256 of fm.exe every load** — often hundreds of MB; LE does not do this every open → skipped when version uniquely maps; cached by path/size/mtime
2. **Full role catalogue per squad player** — deferred off load
3. **Manager signature module scan** — cached per process/module base for the session
4. Still possible leftovers: PowerShell version spawn (first load only if uncached), `scan_module` cold, dossier augment, Next/Tauri dev tax

`glassscout/` → `desktop/` rename attempted; folder locked by running process — close FMT/node/cargo and run T119.
