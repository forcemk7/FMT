---
id: T029
title: Suggest uses labeled FM influence; account for real mentees; next action if stuck
status: done
priority: 2
owner: auto
claimed_at: 2026-08-13T11:00:00Z
started_at: 2026-08-13T11:05:00Z
completed_at: 2026-08-13T11:15:00Z
depends_on: [T027]
---

# T029 — Don't Suggest FM-dead triangles; cover the ~5 mentees; say why / what next

## Why

**Loop break (behavior):** Suggest still offers groups where **in-game influence between members is none**. Attr-proxy `light` ≠ FM arrows. User can wait for Dynamics to drift — they should not have to. Senior FT: **~5–6 real mentee targets**; not all seated. If a kid is skipped because **no safe mentor** or **already-great HA**, that is OK **if the UI says so**.

T025 banned attr-scored all-`none` and remembers dissolved trios. Residual: unlabeled triples still pass on **proxy** influence; no coverage list; dead group = dissolve only, no replacement for that kid.

## Scope

- In: if the user has labeled **any** High→Low / Mid→Low edge as `none` for a triple, Suggest **never** re-offers that triple (already partial — verify + extend to unlabeled-proxy vs labeled-none)
- In: after a dead (all-`none`) dissolve, **immediately Suggest a replacement** for the same Low/kid if one exists; else show why not
- In: Mentoring board (or status line) lists **mentee targets** (age &lt; 24, complete enough): seated / skipped + one-line reason (`already elite HA`, `no safe senior`, `no unused influence path`, `incomplete attrs`)
- In: Suggest must not invent FM influence; unlabeled = proxy only, and **dead-labeled** always wins
- Out: "play them more" as a game coach; modeling form/tenure in extract (T001); inventing Det/Lea (T014); card redesign (T028)

## Acceptance criteria

- [x] A triple the user labeled with downward edges `none` is never Suggested again (reload-safe)
- [x] Dissolve dead group → next unused safe group for that Low seat is offered (board Suggest or inline), or an explicit "no replacement" + reason
- [x] User can see which of the young pool are unseated and **why** (covers the "5–6 mentees not all accounted for" case)
- [x] Tests: labeled-none excluded; skip-reason for elite HA and no-safe-mentor

## Notes / pointers

- `passesMentoringSuggestGate`, `findInfluenceSafeMentoringGroups`, `isMentoringInfluenceSubject`, `MENTEE_HA_ELITE`
- Younglings also filtered by Det ≤ squad mean — may hide mentees; if a named kid is skipped only for that, surface it
- Do not weaken T025 Det-harm / HA-inversion bans

## Progress

**Shipped**
- Labeled High→Low / Mid→Low `none` writes the triple into persisted `rejectedGroupKeys` (Dynamics save + dissolve). Unlabeled still uses attr proxy; labeled `none` always wins. `MENTORING_LOGIC_REV` 13.
- Dead (all-`none`) dissolve commits the next unused safe trio for that Low via existing Suggest commit, or status `No replacement for {kid}: {reason}`. No "play them more".
- Mentoring status line lists young targets: seated / skipped (`already elite HA`, `no safe senior`, `no unused influence path`, `incomplete attrs`, `Det above squad mean`).
- Tests in `tests/mentoring.test.ts`: labeled-none excluded after reject key; elite HA skip; no-safe-senior skip; replacement for same Low after dead key.

**Verified:** `npm test` (129 pass), `npm run typecheck`.

**Residual risk:** Coverage re-runs the Suggest finder on Mentoring render (FT-sized). Manual FT click-through (label none → dissolve → replacement or reason) left to the user. Unlabeled proxy `light` is still not FM influence until T001 extract.
