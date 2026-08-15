---
id: T049
title: HA Group column — 3 checks create; # deletes
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T036]
---

# T049 — Header is Group; third check assigns the unit

## Why

**Loop:** capture a mentoring unit from the HA table. T036 still needs a header **button** after three checks. User: that cell is a column like the others; checking three players **is** the assign; clicking the number already clears the group.

## Scope

- In: Leading column header is **Group** (same header chrome as Name / Unit / Age — not a button). Tooltip: Mentoring group
- In: When the third eligible checkbox is checked, create the unit immediately (same `upsertMentoringGroup` / size-3 / eligibility gate as T036). Checks become group **#**
- In: Clicking an existing **#** still **deletes that whole group** (already `deleteMentoringGroup` — keep)
- Out: T048 (claimed — do not steal). Suggest / auto-pick who to check. New group size. Mentoring tab redesign. 1–2 checks creating a group

## Acceptance criteria

- [x] No “Add mentoring unit” button in the header
- [x] Check 3 filtered eligible players → group appears with a number; Mentoring stack has the same trio
- [x] Check 1 or 2 → no group yet
- [x] Click the number → group gone from table and Mentoring stack
- [x] Row click still drives ≥ filters; checkbox / # click does not
- [x] Invalid 3rd check (already grouped / ineligible / max groups) does not create; short title/tooltip OK

## Notes / pointers

- `toggleSquadHaUnitCheck` / `squadHaAddMentoringUnitGate` / `addMentoringUnitFromSquadHaTable` in `web/squad-ha-table.ts` + `web/main.ts`
- Header today: `.squad-ha-add-unit` in `renderSquadHaTable`
- Call create from the 3rd-check path; drop the header button listener

## Progress

- Header is **Group** (tooltip Mentoring group); dropped `.squad-ha-add-unit` button.
- Third eligible check calls `addMentoringUnitFromSquadHaTable` (`upsertMentoringGroup`, size 3). 1–2 checks stay pending.
- Invalid 3rd (grouped / ineligible / max groups) reverts the check; checkbox title is the gate reason.
- `#` click still `deleteMentoringGroup`. Checkbox / `#` still stopPropagation so row ≥ filters stay separate.
- Verified: `npx vitest run tests/squad-ha-table.test.ts` (51 pass); `tsc --noEmit` clean. Did not touch T048.
