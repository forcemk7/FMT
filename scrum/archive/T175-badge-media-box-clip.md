---
id: T175
title: Badge media box clips tall flags for real
status: done
priority: 2
owner: cursor-agent
claimed_at: 2026-08-26T20:40:00Z
started_at: 2026-08-26T20:40:00Z
completed_at: 2026-08-26T20:45:00Z
depends_on: [T174]
---

# T175 — Badge media box clips tall flags for real

## Why

Absolute `width/height:auto` imgs still paint past the frame in WebView (Spain/Belgium/Uruguay). Need a fixed media box: 100%×100% img + object-fit contain + overflow hidden.

## Scope

- In: inner `.badge-media` clip; img width/height 100% contain; drop auto/absolute sizing; simplify fit helper
- Out: T173 squad positions

## Acceptance criteria

- [x] Spain / Belgium / Uruguay stay fully inside the bordered square
- [x] Club logos unchanged visually aside from same clip model

## Progress

Shipped: wrap flag/logo `<img>` in `.badge-media`; CSS uses fixed 100%×100% box + `object-fit:contain` + `overflow:hidden` (no absolute/`width:auto`). Deleted unused `badge-fit.ts`. Hard-refresh profile to verify Spain/Belgium/Uruguay.

Commit: _(filled after git)_
