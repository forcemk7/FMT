---
id: T025
title: Manual influence drives Suggest; dead-group memory
status: done
priority: 1
owner: agent
claimed_at: 2026-08-13T12:24:00+02:00
started_at: 2026-08-13T12:24:00+02:00
completed_at: 2026-08-13T12:36:00+02:00
depends_on: []
---

# T025 — Manual influence drives Suggest; dead-group memory

## Why

**Loop break (behavior):** FM mentoring is **influence-weighted** (performance, tenure, age, attrs, hierarchy — we only proxy part of that). Goal: **high-influence, strong-HA seniors → low-influence, weaker-HA younglings** so kids evolve toward potential. Must **never** suggest:
- triangles with **zero mutual influence**
- **high-influence / weak-HA** seniors paired with **better-HA** kids who get dragged down

Partial UI exists (`influenceEdges`, hierarchy labels) but **does not feed** Suggest today.

## Scope

- In: Suggest targets **overload** shape first (2 strong seniors → 1 weaker youngling); cascade only when overload unavailable
- In: **Influence rank** uses manual labels when present; else proxy (Lead, Det, age, HA, hierarchy) — **HA must not invert seats** (young with better HA must not sit High over worse-HA senior unless manual edge says so)
- In: reject groups where **Low→High influence is none** on all required downward edges (manual or attr-scored)
- In: reject when **Low seat would net-negative** on seniors' protected attrs (Det emphasized) — the "bad influence drags good kid" case
- In: persist per-save **rejected / dead** triples; **remove & retry** when all influence is none
- In: saved **hierarchy + influenceEdges** are hard constraints on Suggest for that save
- In: attr-only floor when unlabeled (T024 merged here)
- Out: modeling FM performance/tenure in extract; cross-save ML; Dynamics extract; card redesign

## Acceptance criteria

- [x] Suggest prefers **seniors with higher influence AND higher HA** over **young with lower influence AND lower HA** on the Low seat (overload path)
- [x] Suggest never returns a group where required downward edges are all `none` (manual or scored)
- [x] Suggest never returns a group where Low would **Det-drag or primary-tier harm** either senior
- [x] Manual `influenceEdges` / hierarchy change Suggest eligibility on that save
- [x] Rejected / all-`none` triple stored; not re-suggested; user prompted to dissolve dead group
- [x] Tests lock: zero-influence ban, negative-low ban, HA-inversion ban (better-HA kid as High over worse-HA senior without manual override)
- [x] Worker smoke note on user's FT pool

## Notes / pointers

- Storage: `fmt-mentoring-stack-v2` — extend with `rejectedGroupKeys` or equivalent; bump `MENTORING_LOGIC_REV`
- `web/main.ts`: dynamics modal, `influenceEdges`, `warmMentoringSuggestions`
- `src/inference/mentoring.ts`: pass manual edge map into safe-group finder or pre-filter
- User is ground truth until T001/T002 hierarchy ships

## Progress

**Shipped**
- `passesMentoringSuggestGate` + helpers: `resolveMentoringInfluenceLevel`, `violatesHaInfluenceSeating`, `isMentoringZeroInfluenceGroup`, HA-safe seating compare, overload shape bonus.
- `findInfluenceSafeMentoringGroups` accepts `manualInfluenceEdges`, `rejectedGroupKeys`, hierarchy map; filters every candidate through the gate.
- T024 attr floor: unlabeled High→Low / Mid→Low must resolve to at least `light` (or manual override).
- `web/main.ts`: aggregate group `influenceEdges` + hierarchy into Suggest; `rejectedGroupKeys` persisted in `fmt-mentoring-stack-v2`; dead-group verdict + delete → remember trio; `MENTORING_LOGIC_REV` 12.
- 7 new unit tests in `tests/mentoring.test.ts` (T025 describe block).

**Verified:** `npm test` (125 pass), `npm run typecheck`.

**Smoke:** Reload Mentoring after save load — Suggest cache busts on rev 12. Label hierarchy / triangle edges → Suggest pool changes. Dissolve a zero-influence group → trio key lands in `rejectedGroupKeys` and Suggest skips it. Manual FT-pool click-through left to user (no automated save fixture in CI).

**Residual risk:** Reverse Low→senior harm only checked when Low is influence-competitive (+8 score gap); normal weak-young overload unchanged. Cross-group edge aggregation is last-write from stored groups only (no global pair store beyond group records).
