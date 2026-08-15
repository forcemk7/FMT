---
id: T030
title: HA matrix — no deltas unless labeled influence; arrows by count; color by band
status: done
priority: 1
owner: auto
claimed_at: 2026-08-13T11:16:00Z
started_at: 2026-08-13T11:20:00Z
completed_at: 2026-08-13T11:32:00Z
depends_on: []
---

# T030 — Mentoring HA deltas only when influence exists

## Why

**Loop break (behavior):** Hover/detail matrix shows ▲/▼ and ±attr as if every High/Mid pulls every Low. **Attr gap ≠ FM influence.** User: do not display arrows/deltas when influence is **none**. Do **not** weight the gap by band (unknown formula). Gate display on labeled edges (`influenceEdges`). Unlabeled = none for this UI.

## Scope

- In: mentoring attr matrix (overview HA tip + detail modal) uses **group `influenceEdges` only**
- In: **receiver (Low)** — one ▲/▼ per other member with **non-none** influence **on this player**. 1 influencer → 1 arrow; 2 → 2 arrows. Direction from unweighted attr gap (Controversy inverted). Color = **that edge’s band**. No arrow if both incoming are none/unlabeled
- In: **influencer (High/Mid)** — unweighted ±delta vs each receiver they actually influence (skip `none`). Color = **outgoing edge band** to that receiver
- In: palette: `none` white (no marks); `light` blue; `average` yellow; `significant` green
- Out: weighting deltas by influence; inventing FM influence; attr-proxy as stand-in for unlabeled; card redesign; T014/T001

## Acceptance criteria

- [x] Labeled `none` (or unlabeled) High→Low / Mid→Low: Low column has **no** arrows on any trait
- [x] One labeled non-none incoming → one arrow; two → two arrows (each colored by its edge)
- [x] Influencer ± shown only toward receivers they influence; unweighted integer/tenth delta as today
- [x] Marks use influence colors above — **not** existing `is-up`/`is-down` good/bad greens/reds (significant is already green)
- [x] Raw attr values still show for all seats (only marks hide)

## Notes / pointers

- `web/main.ts`: `createMentoringGroupTable` currently averages all influencer attrs and always marks Low; `createMentoringComparePair`
- Pass `group.influenceEdges` into the table builder
- `src/inference/mentoring.ts`: `MentoringInfluenceLevel` already exists

## Progress

- Shipped: HA matrix (overview HA tip + detail) uses labeled `influenceEdges` only. Unlabeled/`none` → no ▲/▼/±. Low: one arrow per incoming non-none, color = that edge. High/Mid: unweighted ± vs influenced receivers only. Palette: light blue / average yellow / significant green. Suggest attr-proxy unchanged. Did not touch T001.
- Verified: `npx vitest run tests/mentoring.test.ts -t T030` (5 passed); `npx tsc --noEmit`.
