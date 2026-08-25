---
id: T128
title: FMT attribute good/mid/bad colors
status: done
priority: 4
owner: cursor-worker
claimed_at: 2026-08-25T16:40:00Z
started_at: 2026-08-25T16:40:00Z
completed_at: 2026-08-25T16:42:00Z
depends_on: [T127]
---

# T128 — FMT attribute good/mid/bad colors

## Why

OG FMT spreadsheet tones make the desk readable at a glance. GlassScout desk is monochrome.

## Scope

- In: Same rules as OG: mid > 14 → good; 0 < mid < 6 → bad; else neutral; **Controversy inverted**
- In: Apply on attributes desk values (visible/hidden/personality)
- Out: Full theme redesign, dark mode work

## Acceptance criteria

- [x] Desk values use good/bad/neutral colors per OG rules
- [x] Controversy uses inverted thresholds

## Progress

`attribute-tone.ts` + desk `.attr-tone-good|bad|neutral` (OG greens/reds).
