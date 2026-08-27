---
id: T179
title: Dashboard widgets as distinct panels
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-27T11:05:00Z
started_at: 2026-08-27T11:05:00Z
completed_at: 2026-08-27T11:10:00Z
depends_on: [T178]
---

# T179 — Dashboard widgets as distinct panels

## Why

T178 peeks read as one continuous list on the dark shell (invisible hairlines, title/arrow wrap). Widgets must be separate visual containers.

## Scope

- In: Reuse elevated `screen-panel` chrome for each dash widget; visible gap + 2×2 grid; title+chevron one row; force vertical peek rows inside each panel
- Out: New widget types; framework; content rule changes

## Acceptance criteria

- [x] Four clearly separate bordered panels on Dashboard (not one stacked sheet)
- [x] Widget title and → sit on one header row
- [x] Peek players stack vertically inside each panel (not a face strip)
- [x] Header still opens full view; row still opens player

## Progress

Shipped: each widget uses `screen-panel` + elevated dark panel chrome; header label+chevron row; peek list forced column. Hard-refresh Dashboard to verify four boxes.

Commit: `33c42b4`
