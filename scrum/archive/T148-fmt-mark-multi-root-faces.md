---
id: T148
title: FMT mark only; multi-root faces
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-25
started_at: 2026-08-25T21:00:00Z
completed_at: 2026-08-25T21:15:00Z
depends_on: [T146, T147]
---

# T148 — FMT mark only; multi-root faces

## Acceptance criteria

- [x] Header shows FMT mark only (no GS crosshair, no club desk)
- [x] Settings lists multiple graphics folders (one per line)
- [x] Resolve across all roots; icon falls back to portrait; UI prefers portraits
- [x] Direct face_/iconface_ preferred; huge config.xml skipped (>8MB)

## Progress

Why faces failed: single root + list views asked for icons; empty face-cache showed resolve never hit. Fix = multi-root + portrait-first + direct file scan. cargo check ok.
