---
id: T156
title: Equal fixed badge slots on profile facts
status: done
priority: 2
owner: cursor-agent
claimed_at: 2026-08-26T17:25:00Z
started_at: 2026-08-26T17:25:00Z
completed_at: 2026-08-26T17:28:00Z
depends_on: [T154]
---

# T156 — Equal fixed badge slots on profile facts

## Why

Nation and club PNGs (cutouts) used different box sizes. Missing badges returned `null` and collapsed the slot, so labels shifted.

## Scope

- In: same 36×36 square for nation + club on profile facts; contain PNG; always reserve slot; fixed fact min-width
- Out: T155 dark shell; invent higher-res pack pixels

## Acceptance criteria

- [x] Nation flag and club logo occupy the same square size on the profile fact row
- [x] Loading/miss still reserves that square — Nationality/Club text does not jump
- [x] PNG cutouts use contain (no crop)

## Progress

Equal 36×36 slots; empty placeholder when miss/loading; profile always mounts a slot. CSS contain for PNG cutouts.
