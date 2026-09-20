---
id: T087
title: Progress GK vs outfield CA layout
status: blocked
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T094]
---

# T087 — Progress GK vs outfield CA layout

## Why

T078 shipped column chrome; keepers still do not show **goalkeeping abilities**, and outfield still lacks the in-game Goalkeeper Rating. Frozen until a **native** Career Save extracts a non-empty `players[]` (T094). Do not claim while T094 is open.

## Scope

- In: Progress CA chips match FM attribute screens:
  - **GK:** Goalkeeping | Mental | Physical | Technical (Free Kick Taking, Penalty Taking, Technique)
  - **Outfield:** Technical | Set Pieces, Mental, Physical | Goalkeeping (Goalkeeper Rating *x* / *xx*)
- In: if those values are already on the CA card, show them; if extract never reads GK attrs / GK rating, extend the **existing** CA-card walk (not a third extract)
- Out: Squad HA table columns. Suggest. www (T077). New save-fitted constants. Changing who is at-club vs loaned

## Blind (non-negotiable)

- Do **not** git add `data/saves/` or `*.fm`. Do **not** mmap live `games/*.fm`

## Acceptance criteria

- [ ] Selecting a GK on Progress shows Goalkeeping abilities (not an empty GK block / outfield-only Technical list)
- [ ] Selecting an outfield player shows Technical + Set Pieces, Mental, Physical, and Goalkeeper Rating *x* / *xx* when the card has it (`—` if missing)
- [ ] HA pack band stays below, separate (T078)
- [ ] One git commit `T087: …` on FMT/ — no `.fm` in the commit

## Notes / pointers

- T078: `web/attribute-evolution.ts`, `tests/attribute-evolution.test.ts`. Explicitly out: “No GK/outfield 1–10 ratings (not in extract).”
- Role detection must actually mark GKs; a missed GK role is why keepers look like outfielders

## Progress

_(worker fills)_
