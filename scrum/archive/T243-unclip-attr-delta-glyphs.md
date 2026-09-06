---
id: T243
title: Unclip attr Δ glyphs without row-height shift
status: done
priority: 2
owner: auto
claimed_at: "2026-09-06T21:32:00+02:00"
started_at: "2026-09-06T21:32:00+02:00"
completed_at: "2026-09-06T21:41:00+02:00"
depends_on: [T239]
---

# T243 — Unclip attr Δ glyphs without row-height shift

## Why

T239 locked Δ width so within-role hops stayed stable, but a fixed-height `overflow:hidden` Δ slot shaved glyphs vertically. Values looked fine; Δs looked misaligned/clipped.

## Scope

- In: Drop fixed Δ slot height + vertical clip; center-align Δ with value; keep fixed width track so empty vs filled Δ cannot change row height (value cell already sets height)
- Out: Widening Δ column; GK/outfield unify; Match experience

## Acceptance criteria

- [x] Δ glyphs are not vertically clipped
- [x] Δ and values share the same type metrics and vertical alignment
- [x] Empty vs filled Δ does not alter attribute row height
- [x] One commit `T243: …`

## Progress

- Root cause: `height: calc(value-size * line-height)` + `overflow:hidden` + baseline nudge on Δ slot only
- Fix: remove hard height; `align-items: center`; width track unchanged
- Verified: user confirmed layout intent; ship requested
- Commit: `f0c9d0b83fbdec81231e9a296556cf905165a85b`
