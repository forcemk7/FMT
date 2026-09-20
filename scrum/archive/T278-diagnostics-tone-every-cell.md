---
id: T278
title: Diagnostics tone on every cell + visible cue
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-09-10
started_at: 2026-09-10
completed_at: 2026-09-10
depends_on: [T277]
---

# T278 — Diagnostics tone on every cell + visible cue

## Why

T277 shipped tones only on late `diagnosticCells`, and empty tone spans often did not paint. Owner sees no indicators.

## Scope

- In: Tone cue on **every** Diagnostics table cell (connection + load index)
- In: CSS so the cue is visible (`inline-block`, sized)
- Out: Live progressive fill; new RE

## Acceptance criteria

- [x] Every Diagnostics cell shows a green/yellow/red cue
- [x] Cue visible in fmt-shell dark theme
- [x] One commit `T278: …`

## Progress

Shipped: `DiagnosticCellView` on all Diagnostics rows; tone CSS `display:inline-block` + shell overrides; backend index cells keep their tones. Commit: `508036e`.
