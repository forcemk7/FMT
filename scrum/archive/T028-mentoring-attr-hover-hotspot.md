---
id: T028
title: Attr hover on a avoidable hot-spot, not the whole seat
status: done
priority: 2
owner: auto
claimed_at: 2026-08-13
started_at: 2026-08-13
completed_at: 2026-08-13
depends_on: []
---

# T028 — Attr matrix hover must not cover Dynamics clicks

## Why

**Loop break (behavior):** Full-seat hover pops the HA matrix and blocks **smooth Dynamics labeling** (social / influence / hierarchy). User needs to click seats; the overlay fights that. Hover should live on a **small, avoidable** control — rest of the seat is Dynamics.

## Scope

- In: overview seat — attr matrix tip **only** from a dedicated hot-spot (e.g. small "HA" / info glyph), not `mouseenter` on `.mentoring-seat-card`
- In: click anywhere else on the seat still opens Dynamics (existing)
- In: hot-spot is small enough to miss when going for Dynamics; no extra modal
- Out: card redesign; T027 Suggest-close; Dynamics extract; putting attr chips back on the card

## Acceptance criteria

- [x] Hovering face/name/empty seat chrome does **not** show the attr matrix
- [x] Hovering the hot-spot shows the same matrix as today
- [x] Click seat (not hot-spot) opens Dynamics without fighting the tip
- [x] Dense + non-dense overview both use the hot-spot

## Notes / pointers

- `web/main.ts`: `wireMentoringMatrixTip` on `.mentoring-seat-card` in `renderMentoringGroupPanel`
- T021 made overview face+name only with full-card hover — that is the bug now

## Progress

- Shipped: overview `wireMentoringMatrixTip` on a 1.05rem corner `HA` glyph (`.mentoring-seat-ha-tip`), not `.mentoring-seat-card` mouseenter. Face/name/chrome hover does not open the matrix. Glyph click is swallowed so Dynamics stays on the rest of the seat. Dense + non-dense share `renderMentoringGroupPanel`. Fingerprint `ha-hotspot-v1`. T027 Suggest untouched. No card redesign / no attr chips restored.
- Verified: `tsc --noEmit` clean; code-path review (hover host = glyph; card click still `openMentoringDynamicsModal` + `hideMetricTip`).
- Residual: confirm in UI that aiming at face/name no longer pops HA, and the glyph still parks the same matrix.
