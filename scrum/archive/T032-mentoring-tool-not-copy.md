---
id: T032
title: Mentoring is a tool — faces and rank-chevrons, not status copy
status: done
priority: 1
owner: auto
claimed_at: 2026-08-13T13:05:00Z
started_at: 2026-08-13T13:06:00Z
completed_at: 2026-08-13T13:22:00Z
depends_on: []
---

# T032 — Mentoring is a tool (user does not read)

## Why

**Loop break (behavior):** User does not read websites. T029/T031 copy unseen. T030 matrix not graspable. **User spec (2026-08-13):** under every seat, the **other two** members as `{rank-chevrons} {face}` so influence is glanceable. Hover that row → attr diffs for **that pair only**.

## Scope

### Seat influence row (replaces “pips”)

Under **every** member, list the **two other** group players. Each row:

`{chevrons or "−"} {peer face}`

Labeled influence **this seat → peer** / **peer → this seat** (`influenceEdges`). Unlabeled = none.

**Chevrons (military rank, stacked vertically):**

| Band | Mark |
|------|------|
| none / unlabeled | `−` (no chevrons) |
| light | **1** ▲ or ▼ **blue** |
| average | **2** stacked **yellow** |
| significant | **3** stacked **green** |

**Direction:** ▲ = **this seat exerts** influence on that face (they are the influenced player). ▼ = **that face exerts** on this seat. **Mutual:** both stacks (▲ and ▼), each counted/colored by its own band.

Click **main seat** (face/name) still opens Dynamics. Clicking a peer face in the row is optional — do not steal Dynamics.

### Hover on that container (not the whole card)

Show attr diffs for **only the two players in that pair** (this seat + the hovered peer, or the whole 2-peer row if the hover target is the row).

- Player **receiving**: chevrons (same rank language), no ± required
- Player **exerting**: unweighted ± attr diffs
- **Mutual:** both — chevrons on both, ± on both
- Do not average High+Mid. Do not show the third member. Do not weight by band.

### Rest of T032 (unchanged intent)

- **Mentee strip** — under-24 faces: in-group / free / skipped. Click free → Suggest for that Low. No paragraph
- **Low CA/PA** as two small digits on the main seat face
- Kill `.mentoring-card-why` and coverage essays in `#mentoring-status`
- Out: Talent tab; T001 steal; inventing Det/Lea; generic dots if this chevron row exists

## Acceptance criteria

- [x] Each seat shows the other two peers as `−`/chevrons + face
- [x] 1 blue / 2 yellow / 3 green stacked chevrons match labeled light / average / significant
- [x] ▲ vs ▼ vs both matches exert vs receive vs mutual
- [x] Hover pair container → attr tip for **those two only**; receiver chevrons, exerter ±, mutual both
- [x] Young face strip + free-face Suggest; why-line gone
- [x] Unlabeled edges look like none (`−`)

## Notes / pointers

- `influenceEdges` keys `${fromId}>${toId}`
- `renderMentoringGroupPanel` / T030 matrix can remain behind HA glyph or be replaced by this hover tip — **this row is primary**
- Worker already claimed: **swap pips for this spec**, do not ship dots-only

## Progress

**Shipped**
- Young-pool face strip (seated ring / free ring / skipped mute). Click free → Suggest for that Low (`mentoringReplacementForLow`). No coverage essay in `#mentoring-status`.
- Each seat lists the other two as `{− or rank-chevrons} {face}`. ▲ this→peer, ▼ peer→this, mutual both stacks. 1 blue / 2 yellow / 3 green. Unlabeled/`none` → `−`.
- Hover a peer row → 2-player attr tip only (receiver chevrons, exerter ±, mutual both). HA glyph matrix kept. Main seat click still Dynamics.
- Low CA/PA digits on the main face when known. Why-line removed from card (CSS hide + no render). Did not touch T001. No Talent tab. No generic pips.

**Verified:** `npx vitest run tests/mentoring.test.ts tests/mentoring-stack.test.ts tests/roster-personality-signals.test.ts` (56 pass), `npx tsc --noEmit`.

**Residual risk:** Pair hover and chevron density on dense 6+ group boards need a glance on a live save. Existing groups with no `influenceEdges` show `−` until Dynamics is labeled.
