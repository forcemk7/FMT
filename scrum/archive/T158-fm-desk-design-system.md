---
id: T158
title: Cohesive FM desk design system
status: done
priority: 1
owner: cursor-agent
claimed_at: "2026-08-26"
started_at: "2026-08-26"
completed_at: "2026-08-26"
depends_on: [T153]
---

# T158 — Cohesive FM desk design system

## Why

T155 dark patch fought light `fmt-shell` / light header tokens — surfaces clashed. Loop A needs one FM-inspired palette that makes attr bands and chrome look intentional (mockup + in-game Portal feel).

## Scope

- In: Single token set (deep navy-teal shell, elevated panels, soft borders); dark header matching mockups; Loop A panels/tooltips/rings; keep FM attr RGB bands
- Out: Full recruitment/scout-room restyle; editable theme picker; pitch photo wallpaper

## Acceptance criteria

- [x] No light-gray full-width header strip; shell is unified dark
- [x] Dashboard / Squad / player desk / Settings share same panel language
- [x] Attr mid-band readable; HAS tooltip matches mockup contrast
- [x] `body.fmt-shell` no longer forces light `#eef2ef` canvas

## Progress

- Added `fmt-desk.css` design tokens + Loop A surfaces
- Neutralized light `body.fmt-shell`; removed T155 !important dump
- Attr bands unchanged
- Commit: `97820ff`
