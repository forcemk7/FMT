---
id: T271
title: ME better-move — no equal-rung First
status: done
priority: 1
owner: auto
claimed_at: "2026-09-07T03:27:00+02:00"
started_at: "2026-09-07T03:27:00+02:00"
completed_at: "2026-09-07T03:28:00+02:00"
depends_on: [T270]
---

# T271 — ME better-move — no equal-rung First

## Why

Equal-rung First→First “better move” can mark Schalke II Best while Current is Legia First (Europa). Only higher ladder rung counts until division reputation (T253).

## Scope

- In: `isMatchExperienceBetterMove` = higher band only + top-N rank
- In: Test Legia-style stay vs II First
- Out: Division reputation RE (T253); noted path team→division→reputation on T253

## Acceptance

- [x] No same-band First→First better moves
- [x] Higher rung (U19→First) still works
- [x] Commit `T271: …`

## Progress

- Ripped equal-rung from `isMatchExperienceBetterMove`
- Test: Legia First stays Best vs Schalke II #1
- T253 updated with RE path note
- Verified: 18 tests passed
- Commit: `a0ad3d7`
