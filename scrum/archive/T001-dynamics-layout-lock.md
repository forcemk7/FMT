---
id: T001
title: Lock Dynamics binary layout from ground truth
status: cancelled
priority: 1
owner: auto
claimed_at: 2026-08-13T04:52:00Z
started_at: 2026-08-13T05:05:00Z
completed_at: null
depends_on: [T007, T008, T009, T010, T011, T012, T013]
---

# T001 — CANCELLED

Existed to make Mentoring Suggest honest. Suggest is cancelled. Hierarchy enum is not a product gate. See SCOPE.md (2026-08-13 HQ pivot).

# T001 — Lock Dynamics binary layout from ground truth

## Why

**Loop break (behavior):** Mentoring Suggest still builds **zero-influence** groups and groups where the intended mentee **negatively influences** others. Attr-only proxy is insufficient; Dynamics (hierarchy / social / captaincy) is need-to-have before Suggest/seating can be honest (T002→T003). T014 no longer gates this — Det/Lea honesty stays parallel.

## Scope

- In: ground truth fixtures, binary hunt near FT `listAbs` / team body, produce `dynamics-layout-locked.json` (or equivalent lock artifact) + spike notes for extract wire-up
- In: **full-save brute force** hierarchy RE — no dependency on tier drift / new signings / demotion saves
- In: **what influences it** — correlate screenshot GT hierarchy vs age, HA, Lead, Det, captaincy, social group, tenure-if-known; document proxy weights (does not replace extract)
- Out: extract wire (T002); mentoring/Suggest code (T025); Gilson Det/Lea (T014); Mentoring UX polish; inventing hierarchy from correlation alone

## Acceptance criteria

- [x] Ground truth under `data/fixtures/dynamics-ground-truth-*-wip.json` is complete enough to validate a layout
- [ ] Layout lock artifact exists and is reproducible against the A/B (or demotion) save pair
- [x] Spike/notes document the offset/join path for the next extract wire-up
- [ ] **Brute-force pass** documented + run: full decompressed save scan at **every** labeled `uid`/`jobId` hit (±512 B), FT job-list order tables, social-list segment scans, person-double neighborhood — not only ±256 KiB around `listAbs`
- [ ] Best candidate ≥0.85 match on 23 labeled hierarchy rows **or** explicit negative report listing exhausted strategies
- [x] Out-of-scope quarantine respected

## Brute force (mandatory — no drift gate)

1. **Per-ID neighborhood:** all `uid`/`jobId` occurrences in full `.fm` decompress → scan u8/u16/u32 at fixed deltas; score against 4-tier GT (`teamLeader`…`other`).
2. **FT list order:** hierarchy may be indexed by job-list position — scan parallel arrays length 33 (or 23 labeled subset) near `listAbs` and social motif.
3. **Social sub-order:** within Core / Secondary A lists, GT is hierarchy-sorted — test order-encoded scores, not just membership.
4. **Person / job blob:** scan ±128 B around person-double and HA-pack anchors already used by extract.
5. **Cap-only delta:** A→B changed only cap tail — diff all labeled player neighborhoods between saves to find cap-adjacent fields that did **not** change (hierarchy candidates).
6. **Influence scores, not only 4-tier enum:** scan u8/u16 tables indexed by FT job order / social order that rank-correlate with GT (TL > HI > Inf > Other). Mentoring pairwise arrows may be computed live — still hunt stored scores.
7. **Correlation dump:** for labeled players, table hierarchy vs age/HA/Lead/Det/captaincy/social — ship in spike notes. Proxy for T025 until extract hits.
8. Ship script output under `tmp/fm-spike/`; update spike notes with top-N candidates and mismatches.

Do **not** wait for Florin Gabor tier flip or world-class squad drift.

## Notes / pointers

- README "Dynamics lock path"
- Prefer pure hierarchy-demotion save pair if available
- Scripts live under `scripts/spike-dynamics-*.py`; fixtures under `data/fixtures/`

## Blockers

- Hierarchy **enum** still unlocked. Product unblocked via **T002**: ship cap + social + list-order rank; do not wait on 4-tier labels.
- **No drift gate.**

## Progress

- B screenshots → `dynamics-ground-truth-post-captaincy-wip.json`.
- Binary matches GT: cap-tail Gilson/Radović; social lists identical to A; FT jobs identical; Tusjak still TL in Secondary A.
- Person-double ±96 unchanged for Gilson/Radović/Tusjak/Paco — captaincy is FT-list tail only.
- No full lock JSON (hierarchy missing). See `data/fixtures/dynamics-layout-spike-notes.md`.
- 2026-08-13: clarified demotion is not a user-action gate.
- Opportunistic only: Florin Gabor Others → Influential would help hierarchy A/B if it happens — not a product gate.
