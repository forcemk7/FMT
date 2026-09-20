---
id: T282
title: Settings critical peeks use cell grid visuals
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-09-10
started_at: 2026-09-10
completed_at: 2026-09-10
depends_on: [T281]
---

# T282 — Settings critical peeks use cell grid visuals

## Why

Collapsed section peeks were compact text chips. They must match the expanded diagnostics cells — a one-row preview of the same grid.

## Scope

- In: Collapsed preview = same `DiagnosticCellView` cells in a 3-column grid row
- In: Hide preview when section is expanded
- Out: New RE

## Acceptance criteria

- [x] Preview cells match expanded cell visuals
- [x] One row of up to 3 critical cells when collapsed
- [x] One commit `T282: …`

## Progress

Shipped. Commit: `43b758b`.
