---
id: T136
title: No empty console on installed Windows launch
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-25
started_at: 2026-08-25
completed_at: 2026-08-25
depends_on: []
---

# T136 — No empty console on installed Windows launch

## Why

Installed FMT opens a useless empty terminal with the GUI. Owner rejects that.

## Acceptance

1. Windows release binary uses `windows` subsystem (no console window on normal launch).
2. Rebuild note: owner reinstalls / runs new installer to verify.

## Progress

- `desktop/src-tauri/src/main.rs`: `#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]`
- Debug/`tauri dev` can still show a console if useful; release installer should not.
- Commit: see git.
