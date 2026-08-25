---
id: T122
title: CA/PA/HA on player attributes desk
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-25T17:05:00Z
started_at: 2026-08-25T17:05:00Z
completed_at: 2026-08-25T15:25:00Z
depends_on: []
---

# T122 — CA/PA/HA on player attributes desk

## Why

Owner only uses third-party tools for data FM hides: **CA, PA, HA** (personality pack). FM’s player attributes desk is the right place to show them — complement, not a second squad browser.

## Scope

- In: Map and read **Current Ability (CA)**, **Potential Ability (PA)**, and **hidden/personality attributes (HA pack)** for players FMT can already resolve (start: **managed squad**; wider only if the same offsets work cheaply)
- In: Surface them on the existing **player attributes / profile** UI (“attributes desk”)
- In: Honest empty/`—` when a field is not validated; never invent
- Out: Squad-table redesign, mentor desk, loan desk, world scout UI, writing to FM, BepInEx

## Acceptance criteria

- [x] Managed-squad player profile/attributes desk shows **CA**, **PA**, and **HA pack** fields when mapping validates for the pinned FM build
- [x] If a field cannot be validated: show unavailable/`—` and do not guess
- [x] Load path stays managed-squad-fast (no mandatory full-save index to see these on own players)
- [x] Owner can open a club player in FMT and see the same class of hidden numbers they open Live Editor for

## Notes / pointers

- Benchmark: FM Live Editor (fmeditor.com) — we need the live fields, not LE’s chrome
- Stack: `glassscout/` Tauri connector + Mapping Lab / entity-maps for build SHA `3653C97F…`
- Upstream GlassScout deliberately excluded CA/PA/hidden from product data — this ticket overturns that for FMT
- Modular: reader fields in connector → typed on `LivePlayer` → attributes desk only

## Progress

Shipped:

- Entity-map constants: `playerCaOffset` 612, `playerPaOffset` 614, `personPersonalityOffset` 112 (FSS/CE-aligned for pinned build)
- Connector reads CA/PA as u16 (1–200 or null), hidden attrs from the gated indexes in the 54-byte blob, personality as 8× u8 (1–20 or omit)
- Attributes desk + overview: CA/PA strip, Hidden + Personality columns; `—` when missing
- Unit tests: hidden stay out of visible map; personality range filter
- Verified: `cargo test hidden_and_foot` + `personality_attribute_map_keeps` pass

Residual risk: live CA/PA/HA values still need a side-by-side check vs Live Editor on a managed squad player (offsets candidate, not LE-validated).
