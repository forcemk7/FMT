---
id: T217
title: Forgiving squad search + keyboard path
status: done
priority: 3
owner: cursor-agent
claimed_at: "2026-09-05T20:12:24+02:00"
started_at: "2026-09-05T20:12:24+02:00"
completed_at: "2026-09-05T20:16:17+02:00"
depends_on: []
---

# T217 — Forgiving squad search + keyboard path

## Why

Owner’s Loop A habit is in-game → FMT header search → player desk (attrs / movement / HA). Exact `toLowerCase().includes` fails on diacritics (`ilan kramaric` vs `Ilan Kramarić`). Mouse-only hit picking slows the ping-pong. No new RE — shape the search we already have.

## Scope

- In: fold diacritics (NFD + strip marks) on query and player name before substring match; keep `includes` semantics
- In: keyboard — Ctrl/Cmd+F focuses shell search (select existing text); ↓/↑ move highlight across hits; Enter opens highlighted (or first) hit and clears query; Esc clears query / blurs
- In: unit tests for fold + match (Kramarić cases)
- Out: Levenshtein / typo fuzzy; world search; redesign results panel; `/` chord unless free with Ctrl+F; placement ladder

## Acceptance criteria

- [x] Query `kramaric` (and `ilan kramaric`) matches a squad player named `Ilan Kramarić`
- [x] Ctrl+F (Cmd+F on mac) focuses the header search input when connected
- [x] With hits visible: ↓/↑ change highlight; Enter opens that player’s profile and clears search
- [x] Esc clears the search panel
- [x] Click-to-open path unchanged
- [x] Unit tests cover fold/match; no new live RE

## Notes / pointers

- `desktop/src/components/fmt-app.tsx` (`squadSearchHits` / results list)
- `desktop/src/components/shell-header.tsx` (search `Input`)
- Prefer small domain helper under `desktop/src/domain/` (e.g. `squad-search.ts`)

## Progress

Shipped: `foldSearchText` / `playerMatchesSquadSearch` (NFD + strip marks); header search uses fold match; Ctrl/Cmd+F focus+select; ↓/↑ highlight; Enter opens hit; Esc clears; click path unchanged. Verified: `npx vitest run src/domain/squad-search.test.ts` (4 pass). Manual: load save → type `kramaric` / Ctrl+F / arrows / Enter. Commit: `0817d4d`. T218 ready next (dead-code hygiene).
