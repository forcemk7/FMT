---
id: T127
title: Attribute history plot on player desk
status: done
priority: 3
owner: cursor-worker
claimed_at: 2026-08-25T16:20:00Z
started_at: 2026-08-25T16:20:00Z
completed_at: 2026-08-25T16:35:00Z
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

- [x] Reload with changed values adds points; unchanged fields do not spam
- [x] Per-player desk shows plot + toggles + recent/all-time Δ
- [x] History survives app restart (local persistence)

## Progress

- `domain/attribute-history.ts` — localStorage `fmt.attr-history.v1`, append-only on signature change
- Record on Load Active Save + indexed profile open
- Attributes tab: toggles, SVG plot, Δr / Δ∞
