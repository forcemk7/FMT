---
id: T153
title: FM in-game attr color bands + Settings pickers
status: done
priority: 2
owner: cursor-agent
claimed_at: "2026-08-26"
started_at: "2026-08-26"
completed_at: "2026-08-26"
depends_on: []
---

# T153 — FM in-game attr color bands + Settings pickers

## Why

Loop A desk/squad should match FM’s 4-band attribute colors. Owner can tweak band colors in Settings (fixed ranges).

## Scope

- In: Bands 16–20 / 11–15 / 6–10 / 1–5 with FM RGBs; apply to attrs, HAS chips, Ability/Potential rings (CA/PA via /10)
- In: Settings — 4 color inputs + reset to FM defaults; persist locally; CSS variables
- Out: Editable range breakpoints; extra presets beyond FM default + custom colors

## Acceptance criteria

- [x] Standard attrs use four tones; inverse attrs mirror bands
- [x] Ability/Potential rings use same tones on tenths
- [x] Settings can change the four band colors and reset to FM defaults
- [x] Colors persist across reload

## Progress

- Bands: high/upper/mid/low with FM hex defaults
- Settings AttrColorsPanel + localStorage + CSS vars on launch
- Verified: vitest attribute-tone + has-score; tsc
- Commit: `f69e0f6`
