---
id: T003
title: Mentoring Suggest uses extract cap + social + list order
status: cancelled
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T002]
---

# T003 — CANCELLED

Suggest is not the product. User forms groups in FM and only needs HA numbers to validate. See SCOPE.md (2026-08-13 HQ pivot).

# T003 — Suggest uses T002 dynamics (not the 4-tier enum)

## Why

T002 ships captaincy, social group, `socialRank` (index in that clique, 0 = highest in-group). **Hierarchy enum is still null** and is **not** the same FM field as social rank (see SM note). Suggest still ignores extract. Manual labels remain override.

**Social rank ≠ hierarchy icon.** FM Hierarchy (TL / HI / Inf / Other) is a different screen and different counts (this GT: 3/15/1/4 vs social 14+8+1). List order is **hierarchy-sorted inside a clique**, so `socialRank` is a **within-group sort key**, not a Team Leader label. Gilson is HI but Social Others rank 0; Tusjak is TL but Secondary A; Core mixes TL + HI + Inf + Other.

## Scope

- In: Suggest/seating **bias** from extract when present: captaincy > social group (Core above Secondary above Other) > `socialRank` (lower index stronger) + existing attr/HA/PA gates
- In: manual Dynamics labels **override** extract
- In: `hierarchy` from extract is null — do **not** invent TL/HI from `socialRank`
- Out: T032 UX; T001 enum hunt; T014; new tab

## Acceptance criteria

- [ ] With extract dynamics, Suggest prefers Core / lower `socialRank` / captains as High seats over attr-only when unlabeled
- [ ] Does not emit fake `teamLeader` from rank 0
- [ ] Manual hierarchy/edges still win over extract
- [ ] Tests: fixture trio where Core rank-0 beats Secondary rank-0 on High seat; Gilson-class Other+HI is not labeled TL
- [ ] T025 bans (zero-influence, Det-drag, HA invert) still hold

## Notes / pointers

- `player.dynamics.{captaincy,socialGroup,socialRank}` from extract
- `mentoringHierarchyBias` / `rankMentoringInfluence` — add extract bias without mapping to 4-tier names
- Do not steal T032 / T001

## Progress

_(worker fills)_
