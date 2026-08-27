---
id: T178
title: Compact dashboard as filtered-view router
status: done
priority: 2
owner: cursor-agent
claimed_at: 2026-08-27T10:48:00Z
started_at: 2026-08-27T10:48:00Z
completed_at: 2026-08-27T10:54:00Z
depends_on: [T176, T177]
---

# T178 — Compact dashboard as filtered-view router

## Why

Dashboard should be a routing hub of filtered peeks (FM-style views), not tall full lists. Each widget is one filter; header opens the full view; rows open players.

## Scope

- In: Compact 2×2 (or responsive) Dashboard with four widgets — Movers, Prospects, HAS Top, HAS Bottom; peek caps (~5); widget header → dedicated full list screen; row → player; denser rows; drop Dashboard→Squad CTA (Squad stays in nav)
- Out: Widget framework/builder; pagination; new RE; Tactic/role desks; favorites strip

## Acceptance criteria

- [x] Dashboard shows four separate widgets (Movers / Prospects / HAS Top / HAS Bottom) without needing to scroll through full Top10+Bottom10 stacks
- [x] Peek lists are capped; overflow is on the widget’s dedicated page via header/See all
- [x] Player row opens player profile; widget header opens that filter’s full page
- [x] Full pages list the same filter without peek cap (or a higher practical cap) and support back + player open
- [x] Shell nav still treats these pages as under Dashboard (not new primary tabs)

## Notes / pointers

- `dashboard-screen.tsx`, `fmt-app.tsx`, `shell-header.tsx` Screen union
- Domain: `rankSquadMovers`, `rankSquadProspects`, `squadHasRankings`

## Progress

Shipped: 2×2 compact peeks (cap 5); header → Movers/Prospects/HAS Top/HAS Bottom pages; row → player; Squad CTA removed from Dashboard heading. Verified tsc + vitest (15).

Commit: `c5c1c0b`
