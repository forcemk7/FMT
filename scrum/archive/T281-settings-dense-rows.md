---
id: T281
title: Settings — denser section rows + 3 critical peeks
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-09-10
started_at: 2026-09-10
completed_at: 2026-09-10
depends_on: [T280]
---

# T281 — Settings — denser section rows + 3 critical peeks

## Why

Settings is a grind surface. Page title/subtitle and per-section subtitles add noise. Collapsed rows should show label + key meta, plus up to 3 critical cell peeks; expand still shows the full cell grid.

## Scope

- In: Remove Settings page title/subtitle block
- In: Section summary = icon + label + tone + meta + chevron (no subtitle)
- In: On collapsed summary, show up to 3 critical cells (title: status); expand = full grid
- Out: New RE; renaming nav Settings

## Acceptance criteria

- [x] No page heading / section subtitles
- [x] Collapsed row shows ≤3 critical peeks when present
- [x] Expand still shows all cells
- [x] One commit `T281: …`

## Progress

Shipped: no page heading; section rows are label + peeks + meta; ≤3 critical peeks on collapse; full grid on expand.
