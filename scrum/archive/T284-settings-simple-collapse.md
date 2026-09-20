---
id: T284
title: Settings — simple collapse rows only
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-09-11
started_at: 2026-09-11
completed_at: 2026-09-11
depends_on: [T283]
---

# T284 — Settings — simple collapse rows only

## Why

Collapsed preview rows made Settings worse. Revert to simple expand/collapse: section title + status data point; full cell grid only when expanded.

## Scope

- In: Remove critical peeks / preview row
- In: Collapsed row = icon + title + tone + meta + chevron
- In: Keep full diagnostics cell grid on expand; keep seven sections
- Out: New RE; bringing back page title

## Acceptance criteria

- [x] No preview row under collapsed sections
- [x] Expand still shows full cell grid
- [x] One commit `T284: …`

## Progress

Shipped. Commit: `a412060`. Collapsed = title + tone + status meta; expand = full cell grid. No preview row.
