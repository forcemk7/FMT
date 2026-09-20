---
id: T265
title: Dash identity under name + small-viewport face flex
status: done
priority: 2
owner: auto
claimed_at: "2026-09-07T02:03:00+02:00"
started_at: "2026-09-07T02:03:00+02:00"
completed_at: "2026-09-07T02:05:00+02:00"
depends_on: [T264]
---

# T265 — Dash identity under name + small-viewport face flex

## Why

Age/position belong under the name on every peek (consistent base identity). Small viewports still overflow — faces must shrink with the row.

## Scope

- In: All dash peeks — under name: subtle `{age} · {pos}`; remove age/pos from extras
- In: Ability extras = team + PA/CA; ME extras = from→to + CA/PA (+ rank main)
- In: Small-viewport face/content clamps so peeks don’t overflow
- Out: Changing peek count

## Acceptance

- [x] Every peek shows age·pos under name (when known)
- [x] Age/pos not duplicated in extras
- [x] Small viewport: faces shrink; no widget scrollbar from face overflow
- [x] Commit `T265: …`

## Progress

- Shared `DashPlayerIdentity` — `{age} · {pos}` under name on all peeks
- Ability/ME extras no longer carry age/pos
- Face clamp uses `min(vh,vw)`; tighter ≤1100px breakpoint
- Commit: `1505061`
