---
id: T149
title: Replace GS app icons with FMT mark
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-25
started_at: 2026-08-25T21:05:00Z
completed_at: 2026-08-25T21:10:00Z
depends_on: [T148]
---

# T149 — Replace GS app icons with FMT mark

## Why

Window chrome and taskbar still showed GlassScout G-crosshair. Product is FMT.

## Acceptance criteria

- [x] `src-tauri/icons/icon.ico` + PNG set regenerated from FMT mark (dark + gold FMT)
- [x] Next `app/icon.png` uses same mark
- [x] Header brand is mark-only (no duplicate FMT text)

## Progress

Generated via Pillow from mark colors. Dev/taskbar needs full restart of `fmt.exe` (icons baked at Rust rebuild). Installer rebuild picks up new ico.
