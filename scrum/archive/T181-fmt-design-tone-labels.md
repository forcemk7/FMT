---
id: T181
title: Label attr tones as FMT design scheme
status: done
priority: 2
owner: cursor-agent
claimed_at: 2026-08-27T11:31:00Z
started_at: 2026-08-27T11:31:00Z
completed_at: 2026-08-27T11:34:00Z
depends_on: [T180]
---

# T181 — Label attr tones as FMT design scheme

## Why

Tone hexes are owner preference inherited by FMT, not Sports Interactive / FM in-game chrome. Naming must not claim they are FM colors.

## Scope

- In: Rename `FM_IN_GAME_ATTR_COLORS` → FMT design palette name; fix domain/CSS comments; tests
- Out: Changing hex values; Settings redesign; band threshold changes

## Acceptance criteria

- [x] No product code claims these hexes are FM in-game colors
- [x] Default palette constant name reflects FMT design scheme
- [x] Tests still lock mid `#e6e6fa`

## Progress

Shipped: `FMT_ATTR_TONE_COLORS`; comments on `attr-colors` / `attribute-tone` / desk CSS; dropped `FM_IN_GAME_ATTR_COLORS`.

Commit: _(pending)_
