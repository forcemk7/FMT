---
id: T269
title: ME depth sort exclude focus + Current/Best chrome
status: done
priority: 1
owner: auto
claimed_at: "2026-09-07T03:08:00+02:00"
started_at: "2026-09-07T03:08:00+02:00"
completed_at: "2026-09-07T03:12:00+02:00"
depends_on: [T250]
---

# T269 — ME depth sort exclude focus + Current/Best chrome

## Why

`maxSamePosCa` includes the focus player, so elite CAs tie every First card and order collapses to `teamUid` (Schalke Best/Current not leftmost). Chrome: when Current=Best show Best ribbon; user wants green border + current pill only. Split Current/Best when apart.

## Scope

- In: `maxSamePosCa` = max same-pos CA **excluding** focus
- In: `pickBest` — if Current with `focusRank <= 2`, that card is Best
- In: Chrome — at best: green border + current under-name (no Best ribbon). Else: Current blue border; Best neon green + Best ribbon
- Out: Division difficulty (T253)

## Acceptance

- [x] High-CA focus no longer flattens First card order; strongest *roster* depth leftmost
- [x] Current top-2 stays Best
- [x] Visual rules above
- [x] Tests + commit `T269: …`

## Progress

- `maxSamePosCa` excludes focus; elite-CA order test
- `pickBest` stays on Current when rank ≤ 2
- Panel: no Best ribbon when Current=Best; blue vs neon-green borders
- Verified: `npx vitest run src/domain/match-experience.test.ts` (15 passed)
- Commit: `8783a9a`
