---
id: T021
title: Mentoring overview = face+name only; full HA matrix on player hover
status: done
priority: 1
owner: auto
claimed_at: 2026-08-13T03:38:24+02:00
started_at: 2026-08-13T03:39:00+02:00
completed_at: 2026-08-13T03:40:14+02:00
depends_on: [T017, T018, T019, T020]
---

# T021 — Mentoring overview = face+name only; full HA matrix on player hover

## Why

**Loop break (behavior):** Mentoring page’s job is **see who is grouped** (face + name). Showing a **partial** attr table on the card (Det/Pro/Pre only) is half-assed — splits attention and still isn’t the full HA feedback. User: specialize the view; key info only if at all; **on hover any player → HA table with deltas**.

Screenshot: 5 groups with on-card matrix always visible under seats — contradicts name-first specialization.

## Scope

- In: Mentoring **overview** cards (dense **and** non-dense): **no** on-card attr matrix / compact attr strip. Seats = face + name (+ minimal Dynamics line only if it doesn’t fight scan)
- In: hover any seated player → **full** HA attr×player matrix with deltas (existing tip path; column highlight for hovered player)
- In: click seat → dynamics/influence modal (keep T018)
- Out: Dynamics extract; chip walls; inventing new metrics; T014

## Acceptance criteria

- [x] Overview cards never show an on-card Det/Pro/Pre (or any) attr matrix — including when group count &lt; dense threshold
- [x] Hover seat → full HA table + deltas; hovered column highlighted
- [x] Face + name remain the primary scan; names not fighting a half matrix
- [x] Click → dynamics modal preserved
- [x] No extract changes

## Notes / pointers

- Bug class: non-dense path still mounts `.mentoring-attrs-host` / matrix on card (`renderMentoringGroupPanel`)
- Dense already hid chips; non-dense left “halfway” matrix — remove that for all overview densities
- T020 tip positioning stays

## Progress

- Shipped: `renderMentoringGroupPanel` always seats-only; wires `wireMentoringMatrixTip` + `createMentoringGroupTable(..., playerId)` for every density. Removed overview `.mentoring-attrs-host`. Seats fill shell (CSS). Fingerprint `face-name-only-v1`. Detail modal matrix unchanged. Click → Dynamics unchanged.
- Verified: code-path review (non-dense no longer appends attrs host; hover highlight path shared with T018/T020); typecheck only pre-existing mentoring.ts EOTP errors; no extract edits.
- Residual: confirm in UI that &lt;6 groups no longer show on-card matrix and hover tip still parks correctly.
