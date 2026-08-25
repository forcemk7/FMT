---
id: T145
title: Roadmap stubs use TBD icon (no Later text)
status: done
priority: 2
owner: cursor-agent
claimed_at: 2026-08-25
started_at: 2026-08-25T20:35:00Z
completed_at: 2026-08-25T20:36:00Z
depends_on: [T144]
---

# T145 — Roadmap stubs use TBD icon (no Later text)

## Why

Muted Loop C tabs need a common "not ready" signal without shouting LATER/TBD as chrome text.

## Scope

- In: Replace the `Later` small on non-live nav items with lucide `CircleDashed`. Keep title / aria for accessibility.
- Out: Building those desks; renaming nav labels

## Acceptance criteria

- [x] Live tabs (Dashboard, Squad): no TBD/Later badge
- [x] Muted tabs: icon only (no Later/TBD text in the tab)
- [x] Hover/focus still explains roadmap via title or aria-label

## Progress

Shipped CircleDashed on muted nav; title + aria-label retained. Verified by source review.
