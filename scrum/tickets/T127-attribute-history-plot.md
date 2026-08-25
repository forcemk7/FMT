---
id: T127
title: Attribute history plot on player desk
status: ready
priority: 3
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T126]
---

# T127 — Attribute history plot on player desk

## Why

Owner tracks CA/HA development in a spreadsheet (max-delta only — loses ups/downs). Need append-only history + a desk plot like OG FMT evolution, minimal.

## Scope

- In: On each successful load, append change-points for visible attrs, hidden attrs, CA, PA (never overwrite prior points)
- In: Player attributes desk: toggle series on/off, simple plot, recent + all-time absolute deltas
- Out: Full OG squad-evolution chrome, mentoring, world UI

## Acceptance criteria

- [ ] Reload with changed values adds points; unchanged fields do not spam
- [ ] Per-player desk shows plot + toggles + recent/all-time Δ
- [ ] History survives app restart (local persistence)

## Progress

_(worker fills)_
