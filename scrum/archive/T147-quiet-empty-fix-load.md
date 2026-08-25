---
id: T147
title: Quiet empty desk; fix truncated Load Data
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-25
started_at: 2026-08-25T20:55:00Z
completed_at: 2026-08-25T21:00:00Z
depends_on: [T144]
---

# T147 — Quiet empty desk; fix truncated Load Data

## Why

Header Load Data crushed by `.shell-tools>button{width:34px}`. Empty Dashboard dumped None/None filler.

## Acceptance criteria

- [x] Header Load Data shows full "Load Data" text when disconnected
- [x] Empty Dashboard/Squad: no diagnostic grid of Nones; no "same as header" caption
- [x] FM running / real failure / useful message shown when present; otherwise quiet blank

## Progress

Fixed shell-tools width exception for `.shell-load`. Slimmed LiveDataState to signal-only or empty. Commit below.
