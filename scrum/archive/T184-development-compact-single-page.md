---
id: T184
title: Development desk compact single-page view
status: done
priority: 1
owner: cursor-agent
claimed_at: "2026-08-27T16:24:00+02:00"
started_at: "2026-08-27T16:24:00+02:00"
completed_at: "2026-08-27T16:35:00+02:00"
depends_on: []
---

# T184 done — Development desk compact single-page view

## Why

T183 nested scroll hid the plot. Development is now one compact AttributeDesk (all-time Δ) + plot; click rows / presets to plot any desk field including hidden & personality.

## Acceptance criteria

- [x] Same desk groups as Attributes, compact, all-time Δ
- [x] No nested scroll panes for field lists / timeline
- [x] Plot CA/PA and visible / hidden / personality (mixed scale → shape-normalized)
- [x] Empty / single-observation factual copy

## Progress

- Extracted `AttributeDesk` to shared component; Development uses `deltaMode="allTime"` + compact + row toggle for plot
- Domain `allTimeDeltasFromPoints` / `allTimeDeltasForPlayer`; vitest green; tsc clean
- Commit: `36fe561695d551602cbc1edc690b8f16494dad51`
