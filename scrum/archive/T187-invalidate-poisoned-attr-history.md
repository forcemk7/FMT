---
id: T187
title: Invalidate attr history poisoned by old rounding
status: done
priority: 1
owner: cursor-agent
claimed_at: "2026-08-27T17:11:00+02:00"
started_at: "2026-08-27T17:11:00+02:00"
completed_at: "2026-08-27T17:14:00+02:00"
depends_on: []
---

# T187 done — Invalidate attr history poisoned by old rounding

## Why

Blanket all-time −1 while CA climbed: v1 history baselines used pre-T132 `(raw+4)/5` rounding (~+1 high). Post-T132 loads store FM `(raw+2)/5` → fake career decline.

## Acceptance criteria

- [x] v1 store discarded; Development cannot use poisoned baselines
- [x] New observations append to v2 (`fmt.attr-history.v2`)
- [x] Unit test covers discard of version 1

## Progress

- `STORE_VERSION = 2`, drop legacy `fmt.attr-history.v1` on load; `parseAttrHistoryStore` rejects non-v2
- Reload Active Save once to seed a clean baseline; all-time Δ will be empty until a second change-point
- Commit: (filled after git)
