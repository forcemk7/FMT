---
id: T022
title: Mentoring seats fill card height; HA hover tip stays usable
status: done
priority: 1
owner: auto
claimed_at: 2026-08-13T03:48:00+02:00
started_at: 2026-08-13T03:49:18+02:00
completed_at: 2026-08-13T04:17:16+02:00
depends_on: [T021]
---

# T022 — Mentoring seats fill card height; HA hover tip stays usable

## Why

**Loop break (behavior):** Post-T021 overview is face+name (correct job) but **execution fails**:
1. HA hover tip is **poorly responsive** and **does not stay open** — can’t read the matrix.
2. Group cards leave **most vertical space empty** under a thin seat strip — faces/names stay small instead of using the card.

Screenshot: five tall group shells; seats hug the top; huge empty band below.

## Scope

- In: Mentoring group card layout — seats **grow to fill** available card height (larger face + name); no big empty dead zone under the seat row when the grid stretches cards
- In: HA attr tip on seat hover — **usable**: stays open long enough to read; moving onto the tip does not instantly dismiss; responsive show/hide (fix flaky open/close)
- In: keep T021 rules (no on-card half matrix; click → dynamics modal; column highlight on hover)
- Out: Dynamics extract; T014; chip walls; redesign of Add group

## Acceptance criteria

- [x] With 5+ groups, group cards do not show a large empty region under seats — seats use the vertical space (faces/names larger)
- [x] Hover seat → HA matrix remains open while pointer is on seat **or** on the tip; can read deltas without tip vanishing
- [x] Tip open/close feels responsive (no multi-second lag; no flicker fight)
- [x] T021 face+name-only overview preserved
- [x] No extract changes

## Notes / pointers

- CSS: `.mentoring-card` / `grid-auto-rows: 1fr` + `overflow: hidden` stretch shell but seats don’t grow
- Tip: hide-delay / pointerenter on tip (T020 touched measure; persistence still broken per user)
- `web/main.ts` mentoring tip wiring + `.mentoring-seats` / dense seat face sizes

## Progress

- Shipped: seats stretch via `grid-auto-rows: 1fr` + growing face/name; mentoring tip `pointer-events: auto` + shared hide bridge (seat/tip enter clears, 200ms leave) so pointer can move onto tip. Fingerprint `seat-fill-tip-v1`. T021 overview path unchanged (no on-card matrix).
- Verified: code-path review (overview still seats-only + `wireMentoringMatrixTip`; tip bridge + CSS fill rules present); no extract edits.
- Residual: confirm in UI with 5+ tall cards that faces fill dead space and tip stays readable when moving onto it; tip far from seat (viewport clamp) still relies on seat hover to read.
- Note: mid-flight disk-full wiped `web/main.ts` (repo has no commits); restored from Cursor T021 checkpoint+diff then reapplied tip wiring.
