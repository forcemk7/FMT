---
id: T293
title: Responsive desk layout + UI density preference + minimum viewport
status: ready
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T215]
---

# T293 — Responsive desk layout + UI density preference + minimum viewport

## Why

FMT's core design principle is "no pagination required" — a desk should show everything without scrolling. In practice today that's only true on the one viewport it was built against. Owner's own fullscreen screenshot (Squad → Player Profile, taller-than-standard laptop display) shows a large dead-space band below the content — the desk is fixed/custom-fit to one machine's window height, not actually responsive. Separately: the owner deliberately runs FMT at a small font/UI size (personal preference — reads as more professional), but that may be a readability barrier for other downloaders. Both are the same underlying problem — the app assumes one viewport and one text size — so they're one ticket.

## Scope

- In: Desks (start with Squad → Player Profile, the one in evidence; extend to Dashboard/Squad list/Loans/HoYD/GM) fill available application window space responsively — verified on at least two different viewport heights/aspect ratios, not just the owner's own display
- In: Decide and lock a **minimum supported application viewport/window size** — below it, defined/graceful behavior is allowed to differ; at or above it, "no pagination" must hold
- In: A UI density / font-scale preference in Settings > User Preferences (small = current default size, larger = more readable) — both settings must still satisfy "no pagination" at the locked minimum viewport
- Out: Any chrome color/typeface changes (T139); new desk content; per-attribute color coding
- Out: True fluid scaling to arbitrary tiny windows — the minimum-viewport decision explicitly bounds the problem instead

## Acceptance criteria

- [ ] Player Profile (and Squad) fill available window height/width responsively across at least two tested viewport sizes, no large unused dead space at the owner's own resolution
- [ ] Minimum supported viewport is documented (in `research/` or the ticket Progress) and the no-pagination guarantee is demonstrated at exactly that size
- [ ] UI density preference exists in Settings > User Preferences; default matches today's small size; larger setting still satisfies no-pagination at the minimum viewport
- [ ] One commit `T293: …`

## Notes / pointers

- Evidence: owner screenshot, Squad → Marko Radović profile, fullscreen, taller-than-16:9 laptop display, substantial empty space below the Hidden/Personality/General attribute rows
- Requires T215's User Preferences section to exist before the density toggle can be added
- Sequence before T139 if both are picked up close together — re-skinning colors on a layout about to be restructured is wasted work

## Progress

_(worker fills)_
