---
id: T180
title: Unify attr tone palette as app-wide fundamental
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-27T11:20:00Z
started_at: 2026-08-27T11:20:00Z
completed_at: 2026-08-27T11:24:00Z
depends_on: []
---

# T180 — Unify attr tone palette as app-wide fundamental

## Why

HAS and shell CSS drifted mid to `#9aa0c8`; correct FM mid is R230 G230 B250 (`#e6e6fa`). Attr bands must be one callable palette everywhere (attrs, HAS, rings).

## Scope

- In: Single source in `attr-colors` / `attribute-tone`; CSS defaults all `#e6e6fa` mid; helpers to resolve band → CSS var/class; HAS displays use attr tones (+ gold super only); kill hardcoded mid greys/lavenders
- Out: New Settings UI; band threshold changes; new colors beyond correcting mid drift

## Acceptance criteria

- [x] Default mid band color is `#e6e6fa` everywhere (globals + desk + palette)
- [x] Callers can resolve a tone via one domain API (class and/or CSS var)
- [x] HAS high/upper/mid/low use the same `--attr-tone-*` colors (no separate mid paint)
- [x] Super remains gold for HAS above practical ceiling only

## Progress

Shipped: `toneCssVar` / `toneClassName` / `toneHex` on `attr-colors`; mid locked `#e6e6fa`; globals drift `#9aa0c8` / `#5b5b7a` removed; HAS `HasTone` = `AppTone`. Vitest 12 pass.

Commit: _(pending)_
