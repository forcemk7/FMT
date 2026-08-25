---
id: T133
title: Restore GlassScout native full-save scan on load
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-25
started_at: 2026-08-25
completed_at: 2026-08-25
depends_on: []
---

# T133 — Restore GlassScout native full-save scan on load

## Why

Owner wants to evaluate **upstream GlassScout behavior** (full private-memory player index + tactic manager discovery) before deciding FMT’s load shape. T130 disabled that path; the code is still in `connector.rs`.

## Acceptance

1. `load_active_save` calls `collect_snapshot(true, …)` (GlassScout/T126 path).
2. On a live FM26 save load: `database_scope` can become `full-save-index`, `backgroundPlayersIndexed` > 0 when scan finds world players, and tactic read is attempted via the same scan (may still be `object_not_found` if vtable hits ≠ 1).
3. Board/STATUS notes this is an **owner eval** of native GS — not a permanent LE-speed claim.

## Out of scope

- Dossier requirement
- Installer
- UI skin / mentor desk
- Optimizing the scan

## Progress

- Restored `collect_snapshot(true, …)` in `load_active_save` (desktop connector).
- STATUS + SCOPE note owner-eval load path.
- Verified: code path matches T126/native GS; live FM verify is owner (reload save in FMT).
- Commit: `acd9030`.
