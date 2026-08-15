---
id: T062
title: Mentoring HA arrows = attr will go up/down
status: done
priority: 1
owner: cursor-agent
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T030]
---

# T062 — Receiver arrows follow the number; influencer ± in its own column

## Why

Pair/group HA tip: the influenced player always gets ▼ (T032 “receive”). User: arrows mean **the number will move**. Lower than the influencer → ▲; equal → none; higher → ▼. Band still 1 blue / 2 yellow / 3 green. Influencer keeps ±, but the delta must sit in its own column so 7 and 16 line up (same pattern as Progress T051).

## Scope

- In: Pair hover + group HA matrix. Labeled edges only (T030). Equal (abs gap &lt; 0.05) → no arrow / no ±
- In: Influenced cell: stacked arrows in **attr direction** vs that influencer. Count/color = incoming band (light 1 blue, average 2 yellow, significant 3 green)
- In: Arrow dir is **numeric** (CON included): mentee &lt; influencer → ▲; mentee &gt; influencer → ▼. CON 10 vs influencer 7 → ▼ (will drop)
- In: Influencer cell: unweighted ± = influencer − mentee (CON 7 vs 10 → **−3**). Color = outgoing band
- In: Each player cell is **marks column | value column**. Marks column reserved when empty. Values `tabular-nums`, right-aligned (1-digit and 2-digit share a column)
- Out: Unlabeled → still no marks. Seat **face** chevrons (▲ exert / ▼ receive) unchanged. Suggest. Dynamics extract. Weighting by band. New charts

## Acceptance criteria

- [x] Influencer Det 16, mentee 15, labeled light: mentee **1 blue ▲**; influencer **+1** in the marks column; values 16 and 15 align
- [x] Same pair, mentee Det 17: mentee **1 blue ▼**; influencer **−1**
- [x] Equal Det: value only; marks column empty (width held)
- [x] Average → 2 yellow arrows; significant → 3 green; same direction rule
- [x] CON mentee 10 vs influencer 7, labeled: mentee ▼ (count = band); influencer **−3**
- [x] Unlabeled pair: values only, no arrows/± (T030)

## Notes / pointers

- Bug: `createMentoringPairCell` always `createMentoringRankStack("down", …)` for receive
- `planMentoringPairTraitMarks` / `planMentoringMatrixCellMarks` in `src/inference/mentoring.ts` — dir from numeric gap, not “I am the receiver”
- `mentoringUnweightedTraitDelta` today inverts CON (mentor-better). Arrow/± in this ticket are numeric; do not reuse that invert for dir
- Layout: Progress T051 (`.squad-evo-toggle-delta` reserved column)
- Tests: `tests/mentoring.test.ts` (pair hover currently expects receive chevrons with no attr dir)

## Progress

Shipped: pair hover + group HA matrix arrows follow the numeric gap (mentee &lt; influencer → ▲, higher → ▼, equal / unlabeled → no marks). Influencer ± is influencer − mentee (CON included; no mentor-better invert). Cells are marks | value with a reserved marks column (T051 pattern). Seat face chevrons unchanged.

Verified: `npx vitest run tests/mentoring.test.ts` — 46 passed (T062 cases for light ±1, equal, average/significant count, CON 10 vs 7 → ▼ / −3, unlabeled). `npm run typecheck` clean.
