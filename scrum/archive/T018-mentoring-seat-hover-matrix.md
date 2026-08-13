---
id: T018
title: Mentoring seats larger; attr matrix on member hover with column highlight
status: done
priority: 1
owner: auto
claimed_at: 2026-08-13T01:07:30+02:00
started_at: 2026-08-13T01:08:00+02:00
completed_at: 2026-08-13T01:42:48+02:00
depends_on: [T017]
---

# T018 — Mentoring seats larger; attr matrix on member hover with column highlight

## Why

**Loop break (behavior):** T017 removed chip walls, but the attr table still pops as a bulky overlay that covers other groups, and seats stay small / Dynamics-status heavy — hard to spot Josef Tusjak. User: attr table **only while hovering a member card**; **click** opens dynamics/influence modal; **hovered player’s column highlighted**; member cards **scaled up** with name/image eye-catchy.

## Scope

- In: dense Mentoring overview — enlarge seat chrome (face + name primary; Dynamics status de-emphasized)
- In: attr×player matrix appears only on **hover of a seat** (not sticky / not covering half the board as default)
- In: while hovering a seat, that player’s matrix **column is highlighted**
- In: **click** seat (or clear affordance) opens existing dynamics/influence detail modal — not the matrix as a click trap
- Out: Dynamics extract RE; chip walls; T014; Mentoring Suggest changes

## Acceptance criteria

- [x] At ≥6–7 groups, seated **names + faces** are the dominant scan target (larger than post-T017 if needed)
- [x] Attr matrix not visible until hovering a **member** seat; dismisses on leave
- [x] Hovered seat → corresponding matrix column highlighted
- [x] Click seat opens dynamics/influence modal (matrix is hover-only)
- [x] Board remains scannable while one seat is hovered (tip must not obliterate finding other names)

## Notes / pointers

- Screenshot post-T017: large floating matrix over Groups 2/4/6; Tusjak still easy to miss
- Build on T017 tip wiring; fix placement (anchored to seat, not board-center blob) + column highlight
- `web/main.ts` mentoring dense seats / tip; CSS `.mentoring-seat*`

## Progress

Shipped: denser seats enlarged (face 2.35rem, name 0.9rem; Dynamics muted). Attr matrix wired per-seat hover only with hovered column `is-hover-col`; tip parked beside seat (compact, pointer-events none). Click seat → dynamics modal (hides tip). Fingerprint `seat-hover-v1`. Recovered wiped main.ts/styles.css from Cursor T017 checkpoint mid-flight (disk full). Verified typecheck (no new errors; pre-existing mentoring.ts EOTP only) + code-path review of dense `renderMentoringGroupPanel`.
