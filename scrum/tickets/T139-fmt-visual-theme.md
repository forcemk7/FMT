---
id: T139
title: FMT visual theme (MW90 CTRL 26-inspired chrome)
status: ready
priority: 3
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T138]
---

# T139 — FMT styling

Owner-pleasing colors/typography for the stripped shell, refining the existing direction rather than reinventing it — chrome takes inspiration from MW90's CTRL 26 skin for FM26 (not just leftover GlassScout by accident). Goal: better presentation screenshots and first-run impression for downloads/retention. CSS variables; keep layout modest.

## Scope clarification (2026-09-15, refined 2026-09-16)

This is **visual identity only** — color palette and typeface choice for the shell chrome (header, nav, background, buttons, panel borders). It is:

- Not attribute value color bands (already handled separately: T153, T169, T180, T208)
- Not a light/dark mode switcher — a single brand theme, unless HQ explicitly asks for a toggle before this is claimed
- Not layout/structure and not font **size** — the structural responsiveness work and the UI density (font-scale) preference are a separate ticket, **T293**, since they're a different kind of problem (correctness/usability, not taste) and need their own QA pass
- Should land after or alongside T293 — re-skinning a layout that's about to be restructured is wasted work; sequence T293 first if both are in flight

If a light/dark toggle is wanted, raise it with HQ before claiming — treat as out of scope until then.
