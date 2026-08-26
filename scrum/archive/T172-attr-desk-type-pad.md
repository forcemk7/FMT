---
id: T172
title: Attribute desk header size + separator padding
status: done
priority: 2
owner: cursor-agent
claimed_at: "2026-08-26"
started_at: "2026-08-26"
completed_at: "2026-08-26"
depends_on: []
---

# T172 — Attribute desk header size + separator padding

## Why

Values sat flush against column rules; section headers read smaller than attr names.

## Scope

- In: Match heading size to label/value; right pad before vertical separators
- Out: Layout structure changes

## Acceptance criteria

- [x] Headers ≥ attr name/value font size
- [x] Clear gap between values and column separators

## Progress

- `--attr-label/value/heading-size: 10px`; `--attr-col-pad-end: 14px` on cols 1–2
- Commit: _(filled after git)_
