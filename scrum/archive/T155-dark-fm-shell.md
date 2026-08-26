---
id: T155
title: Dark FM shell background for attr color contrast
status: done
priority: 2
owner: cursor-agent
claimed_at: "2026-08-26"
started_at: "2026-08-26"
completed_at: "2026-08-26"
depends_on: [T153]
---

# T155 — Dark FM shell background for attr color contrast

## Why

FM mid-band attr color (#e6e6fa) fails on the light shell. Match FM’s dark navy/teal desk background so all four bands read correctly.

## Scope

- In: Default shell/canvas/body gradient ≈ FM attrs screen; dark translucent panels for Squad + player desk; light text tokens; Ability ring hubs dark
- Out: Full T139 theme polish; rewriting every legacy light-only screen

## Acceptance criteria

- [x] App shell default is dark navy/teal (not light gray)
- [x] Attribute desk + Squad Ability/Potential mid band readable without wash hacks
- [x] Primary Loop A chrome (header, squad table, dossier panels) uses dark surfaces

## Progress

- Shell tokens → FM navy/teal gradient (`#0b1a27` → `#0e2a2a`)
- Loop A panels + top shell darkened; mid wash removed
- Commit: _(filled after git)_
