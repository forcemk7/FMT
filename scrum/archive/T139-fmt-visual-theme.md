---
id: T139
title: FMT visual theme (MW90 CTRL 26-inspired chrome)
status: done
priority: 3
owner: claude-hq-chat
claimed_at: 2026-09-29
started_at: 2026-09-29
completed_at: 2026-09-29
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

## Progress

**Pass 1 (2026-09-29): minimal first version so the owner could judge the direction.** Everything lives in a new `desktop/src/app/theme-ctrl.css`, imported last in `layout.tsx`, which overrides `fmt-desk.css`'s existing `--shell-*`/`--panel*`/`--chrome-*`/`--control-*` tokens plus a few chrome rules. No component or markup changes.

- Canvas: neutral graphite (`#08090b`/`#0c0d10`, panels `#131519`) instead of the blue-cast navy; atmosphere gradients off; neutral white hairlines.
- Header: flat bar, no glass blur or shadow.
- Nav: uppercase, tracked labels; the active desk is marked by a 2px accent underline and accent icon instead of the gold pill. The underline is drawn inside the button because `.shell-nav` clips overflow.
- A single accent, `--ctrl-accent: #22e0a8` (a sharper take on the existing mint), for Load, toggles, active icons and the focus ring. `--mint` now points at it; gold is left for warning/status tones only.
- Corners: panels 14→6px, chrome 10→4px, controls pill→5px, square toggles.
- Settings section labels are uppercase and tracked.
- Not touched: typeface (still Inter), attribute tone bands, layout, sizes.

**Closed (2026-09-29), owner: "I like it, perhaps it is sufficient".** Verified: dev preview (no FM26 attached), covering the Dashboard header/nav and Settings incl. the User Preferences toggles; no new console errors. Not verified: Squad, Player Profile, Loans, HoYD and GM with a real save loaded. Those desks carry more legacy hardcoded CSS, so stray rounded or blue-tinted bits may remain. That check goes into the end-of-1.28 consolidated test pass with T290/T293; if it finds anything, **reopen T139**, not a new ticket. Revert path: delete `theme-ctrl.css` and its import.
