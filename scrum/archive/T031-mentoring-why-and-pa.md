---
id: T031
title: Mentoring shows why this trio; coverage includes CA/PA
status: done
priority: 2
owner: auto
claimed_at: 2026-08-13
started_at: 2026-08-13
completed_at: 2026-08-13T14:40:00+02:00
depends_on: [T030]
---

# T031 — Why this group (on Mentoring, not a Talent tab)

## Why

**Loop break (behavior):** User does not trust Suggest — wants proof the app knows **who is talent** and **why this trio**. A new Talent tab is **refused** (SCOPE: not in the wedge; scouting zoo is discard). Smallest restore: Mentoring already lists mentee skip reasons (T029) but **group cards do not show why the trio was chosen**. Extract already has CA/PA — coverage does not show them, so “talent” is invisible.

## Scope

- In: persist Suggest `reasons` (or equivalent one-liner) on the group record when Suggest/Add commits; show on the **card** (and detail)
- In: mentee coverage line includes **CA/PA** when known; sort unseated young by PA descending so high-potential kids are obvious
- In: Suggest tie-break: prefer higher **PA** Low seat among otherwise-equal overload groups (do not invent PA)
- Out: **new Talent / Loans-adjacent tab**; wonderkid leaderboard; scouting; “needs mentoring yes/no” as a separate product; T014 invent Det/Lea; Dynamics extract

## Acceptance criteria

- [x] A Suggested group shows a readable why (overload/cascade + at least one concrete reason already produced by the finder)
- [x] Manual Add group without Suggest: no fake why — omit or “manual”
- [x] Coverage lists young targets with CA/PA when extracted (honest `—` if missing)
- [x] Tests: PA tie-break prefers higher-PA Low; missing PA does not crash Suggest

## Notes / pointers

- `MentoringGroupRecord` has no `reasons` today — add optional field, persist in `fmt-mentoring-stack-v2`
- `findInfluenceSafeMentoringGroups` already has `reasons[]`
- Roster `player.ca` / `player.pa` from extract
- Do not steal T030 / T001

## Progress

**Shipped**
- Suggest commits persist finder `reasons` on `MentoringGroupRecord` (`fmt-mentoring-stack-v2`). Card + detail show the why-line (overload/cascade + concrete reason). Manual Add with no Suggest hit omits why — no fake copy.
- Mentee coverage lists `CA/PA` (`—/—` if unknown). Unseated young sorted PA descending. Roster normalize now keeps extract CA/PA so coverage is not always dashes after load.
- Overload Suggest tie-break: equal score → higher known PA Low. Missing / junk PA is not invented and does not crash. `MENTORING_LOGIC_REV` 14. No Talent tab. Did not touch T001.

**Verified:** `npx vitest run tests/mentoring.test.ts tests/mentoring-stack.test.ts tests/roster-personality-signals.test.ts` (51 pass), `npm run typecheck`.

**Residual risk:** Existing saved groups have no `reasons` until re-Suggested. Click-through on a live save left to the user.
