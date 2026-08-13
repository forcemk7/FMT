---
id: T017
title: Mentoring board is name-first — find a player’s group at a glance
status: done
priority: 1
owner: auto
claimed_at: 2026-08-13T00:51:00+02:00
started_at: 2026-08-13T00:52:00+02:00
completed_at: 2026-08-13T00:54:50+02:00
depends_on: [T015, T016]
---

# T017 — Mentoring board is name-first — find a player’s group at a glance

## Why

**Loop break (behavior):** User runs many groups. Job on this page is **spot which group holds a player** (e.g. Josef Tusjak), not read every Det chip. T015/T016 filled cards with attr walls → visual overstimulation; names drown. Screenshot post-T016: seven dense chip blocks; hard to scan for a name.

## Scope

- In: Mentoring overview cards prioritize **readable seated names** (and light Dynamics status). Attr values/deltas **not** on the default card face under density — available on hover and/or existing detail/edit only
- In: with ≥6–7 groups, user can find a named player’s group by scanning names in a few seconds
- Out: Dynamics extract; search box / filter (unless trivial and needed); T014; putting chip walls back

## Acceptance criteria

- [x] Dense Mentoring grid: each seat shows a clear name (primary visual); no multi-row attr chip walls on the default card
- [x] Attr/delta matrix or chips available via hover and/or detail — not deleted
- [x] Spot-check: can locate “Josef Tusjak” (or any seated name) on a 7-group board without reading attr numbers
- [x] No extract changes

## Notes / pointers

- User: “what’s important… quickly identify a group of interest… which group has Josef Tusjak”
- Undo T016 on-card chip density; keep T015’s hover/detail path for full feedback
- `.mentoring-cards` / seat chrome in `web/main.ts` + CSS

## Progress

Shipped name-first dense cards: removed per-seat attr chip walls; seats show name + light Dynamics only (larger dense name type). Full attr×player matrix on seat-area hover tip; detail modal matrix unchanged; non-dense cards still show on-card matrix. Fingerprint `name-first-v1`. Verified typecheck (no new errors; pre-existing mentoring.ts EOTP only) + code-path review of dense `renderMentoringGroupPanel`.
