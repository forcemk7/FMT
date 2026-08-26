---
id: T165
title: Header search fills gap and opens players
status: done
priority: 2
owner: cursor-agent
claimed_at: 2026-08-26T20:40:00+02:00
started_at: 2026-08-26T20:41:00+02:00
completed_at: 2026-08-26T20:45:00+02:00
depends_on: []
---

# T165 — Header search fills gap and opens players

## Why

Loop A: find a squad player from the shell and open the desk. Today the header search is a narrow dead-looking control — gap unused, result names unreadable on dark theme — so the path fails.

## Scope

- In: shell header flex so search grows between nav and load pill; dark-theme readable search results; click → player desk
- Out: world/indexed search, recruitment chrome, new result UI patterns

## Acceptance criteria

- [x] Header search expands into the space between tabs and the game-status / Load pill
- [x] Typing a squad name shows readable hits (name + positions visible on dark shell)
- [x] Choosing a hit opens that player’s profile and clears the query

## Notes / pointers

- `desktop/src/components/shell-header.tsx`, `fmt-app.tsx` (`squadSearchHits` / `global-search-results`)
- CSS: `.shell-nav` / `.shell-tools` / `.shell-search` in `globals.css`; theme `global-search-results` in `fmt-desk.css`

## Progress

Shipped: nav no longer eats the flex gap; `.shell-search` grows between tabs and load pill; dark-shell results panel uses panel tokens so names are readable; click already opened profile (unchanged). Failure mode was light inherited `--text` on white GS results chrome. Commit: `b4423c4` (results theme); layout flex also on main via shell CSS.
