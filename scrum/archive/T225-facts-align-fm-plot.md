---
id: T225
title: Facts strip align + FM-faithful Development plot
status: done
priority: 3
owner: cursor-agent
claimed_at: "2026-09-06T02:50:00+02:00"
started_at: "2026-09-06T02:50:00+02:00"
completed_at: "2026-09-06T02:55:00+02:00"
depends_on: []
---

# T225 — Facts strip align + FM-faithful Development plot

## Why

T224 left nationality/club text off the shared strong baseline (32px bordered badges). Development should match in-game plot: 0–20 grid, smooth horizontal-tangent curves, date ticks, endpoint marker for ability — keep FMT hover.

## Scope

**In:**

- Facts: shrink/strip borders on nation+club icons in strip; strong baseline aligns with Age/Height/etc.; secondary positions stay `player-fact-sub`
- Plot: fixed 0–20 Y with 5-step grid; CA/PA as `/10` on that scale; FM-like smooth paths (horizontal tangents); no resting mid-point dots; ability endpoint gold; axis label Ability/Attributes; keep hover guide + tooltip

**Out:** T190 pack dating; theme; club page

## Acceptance criteria

- [x] Nation/club strong shares vertical rhythm with other fact values; no icon border chrome in strip
- [x] Development plot matches FM look (0–20 grid, smooth flats→curves, dates); hover retained
- [x] One commit `T225: …`

## Progress

Shipped:

- Facts strip: 14px borderless badges; identity row height = strong line-height so nation/club align with Age/etc.
- Plot: fixed 0–20 + grid; CA/PA plotted as /10; horizontal-tangent smooth paths; resting dots removed; gold endpoints when ability-only; hover guide + dots + tooltip kept; FM-ish date ticks

Verified: CSS baseline + FM path contract. Commit SHA after commit.
