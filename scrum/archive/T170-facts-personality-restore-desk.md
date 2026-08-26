---
id: T170
title: Personality/Media in facts grid; restore attribute desk layout
status: done
priority: 1
owner: cursor-agent
claimed_at: "2026-08-26"
started_at: "2026-08-26"
completed_at: "2026-08-26"
depends_on: []
---

# T170 — Personality/Media in facts grid; restore attribute desk layout

## Why

Personality / Media Handling belong in the player facts strip (own headers), not under the name. T163 accidentally swapped Attribute Desk markup to `attr-desk-*` classes with no CSS — rows collapsed into one line.

## Scope

- In: Facts cells for Personality + Media Handling; restore 3-column `attribute-desk-row` / `attribute-column` desk; General stays Ability + Potential only
- Out: Traits RE; changing personality HA pack column

## Acceptance criteria

- [x] Facts strip shows **Personality** and **Media Handling** with separate headers
- [x] Name header no longer carries the personality/media subtitle line
- [x] Attribute Desk is 3-column again (name left / value right per row)
- [x] General column still Ability + Potential only

## Progress

- Restored `attribute-desk-row` / `attribute-column` markup (CSS already present)
- Facts cells after CA/PA; removed name subtitle
- Commit: `6a48a21`
