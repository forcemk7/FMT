---
id: T208
title: Five-band attr tones + SD model + dark-green Super
status: done
priority: 2
owner: cursor-agent
claimed_at: "2026-09-04T06:45:00+02:00"
started_at: "2026-09-04T06:46:00+02:00"
completed_at: "2026-09-06T00:10:00+02:00"
depends_on: []
---

# T208 — Five-band attr tones + SD model + dark-green Super

## Why

Loop A/B: elite attrs need a fifth band that beats neon. Owner wants to **try** (1) assumed N(10,3) z-score bulks and (2) dark-green Super for 19–20 — revert **both** together if QA fails, then archive.

## Scope

- In: `attributeBand` via z vs μ=10, σ=3; `AttributeTone` includes `super`; Super hex `#1b7a34`; neon stays high; inverse via `21−value` (Super ↔ 1–2); CA/PA tenths; HAS maps onto same bands; tests
- Out: Settings picker rebuild; fitted live-squad μ/σ; permanent commit until owner QA

## Acceptance criteria

- [x] SD bands: Super z≥+3 (19–20), High z≥+2 (16–18), Upper z≥+1 (13–15), Mid |z|<1 (8–12), Low z≤−1 (1–7)
- [x] Inverse: only 1–2 Super
- [x] Roles: Low/Mid/Upper kept; High solid green `#3abd52` (blue-weight); Super neon `#65e53a`
- [x] Deltas: gains → Super neon; drops → Low red (inverse attrs flipped)
- [x] Ring fill: range % (attr/20, CA·PA/200, HAS practical span); color stays zigma
- [x] Vitest
- [x] Owner QA — keep SD bands + palette for now (neon/High separation imperfect but ok)

## Notes / revert

Prior 4-band fixed cuts were 16–20 / 11–15 / 6–10 / 1–5 (no Super). Experiment kept.

## Progress

Owner kept SD bands + palette (High `#3abd52`, Super `#65e53a`). Deltas Super/Low. Squad rings: color via zigma; fill via range % (HAS practical floor→ceil). Vitest OK. Commit `4ea2285`.
