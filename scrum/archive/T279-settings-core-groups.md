---
id: T279
title: Settings — FM26/Club/Teams/Players/Affiliations/Graphics/Scores
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-09-10
started_at: 2026-09-10
completed_at: 2026-09-10
depends_on: [T278]
---

# T279 — Settings — core groups + nested diagnostics

## Why

Standalone Diagnostics is hard to use. Settings should follow the real groups (FM26, Club, Teams, Players, Affiliations, Graphics, Scores), each with diagnostics at the bottom of its expand, and a section tone with optimistic floor.

## Scope

- In: Remold Settings into those seven sections (literal labels)
- In: Diagnostics nest at the bottom of each expanded section
- In: Section tone = optimistic floor (all green → green; critical red → red; else yellow)
- In: Remove standalone Diagnostics island
- Out: New RE; live progressive fill; theme work

## Acceptance criteria

- [x] Settings shows FM26, Club, Teams, Players, Affiliations, Graphics, Scores
- [x] Each expand has a Diagnostics nest with relevant cells + tones
- [x] Section header tone uses optimistic floor
- [x] No standalone Diagnostics dump
- [x] One commit `T279: …`

## Progress

Shipped: seven Settings groups; nested Diagnostics per section; optimistic floor on section dots; standalone Diagnostics removed; Graphics body reused under Graphics.
