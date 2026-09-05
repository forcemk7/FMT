---
id: T220
title: Move R&D knowledge to research/
status: done
priority: 4
owner: cursor-agent
claimed_at: "2026-09-05T21:59:13+02:00"
started_at: "2026-09-05T21:59:13+02:00"
completed_at: "2026-09-05T21:59:13+02:00"
depends_on: [T219]
---

# T220 — Move R&D knowledge to research/

## Why

Owner wants R&D afforded its own root folder so compounded FM knowledge is centralized and publishable — not buried in the scrum process board.

## Scope

- In: `research/README.md`, move `FM-ECOSYSTEM` → `research/ecosystem.md`, `FM-RECIPES` → `research/recipes.md`
- In: Retarget AGENTS, scrum README, SCOPE, STATUS, `fm-live-read.mdc`
- Out: Splitting recipes into many topic files; product code; rewriting SCOPE north stars

## Acceptance criteria

- [x] Knowledge lives under `research/`; scrum no longer hosts the books
- [x] Worker/agent pointers updated
- [x] One commit `T220: …`

## Progress

Shipped `research/` home. Commit: `a99d850`.
