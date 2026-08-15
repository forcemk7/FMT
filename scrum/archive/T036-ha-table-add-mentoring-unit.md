---
id: T036
title: HA table → Add mentoring unit (checkbox + group #)
status: done
priority: 1
owner: auto
claimed_at: 2026-08-13T16:19:00Z
started_at: 2026-08-13T16:22:00Z
completed_at: 2026-08-13T16:26:00Z
depends_on: [T035]
---

# T036 — Capture mentoring units from the filtered HA table

## Why

After ≥ filter, the surviving rows **are** the mentoring unit. User should check them and **Add mentoring unit** here — not re-pick on the Mentoring tab. Not Suggest: they choose who.

## Scope

- In: Leading column on Personalities HA table: checkbox when unassigned; when in a mentoring group, show **group number** (1-based index) instead of a bare check — click removes from that group
- In: Header control **Add mentoring unit** (or equivalent): creates a group from **checked** rows into the **existing** Mentoring stack (`upsertMentoringGroup` / same store Mentoring tab uses)
- In: Respect existing group size / seat rules already in Mentoring (do not invent a new group model). Disable Add when selection is invalid; short reason in title/tooltip OK, no essay
- In: Row click for ≥ filter stays; checkbox click must **not** toggle the filter preset
- Out: Suggest / auto-seat / influence AI; Dynamics; rebuilding Mentoring board UX; T014

## Acceptance criteria

- [x] User can check 2–3 (or whatever the existing Mentoring create rule allows) filtered players and Add → group appears in Mentoring stack
- [x] Assigned players show group # in the leading cell; remove from group works from that cell
- [x] Filter click (row) and check (cell) do not fight each other
- [x] No Suggest / auto-pick of mentors
- [x] Mentoring tab still shows the same groups (one store)

## Notes / pointers

- `web/mentoring-stack.ts` `MentoringGroupRecord`; `upsertMentoringGroup` / `deleteMentoringGroup` / `canCreateMentoringGroup` in `web/main.ts`
- Personalities table: `renderSquadHaTable` / T035 unit column
- Screenshot: filtered list already looks like ready units

## Progress

- Shipped leading checkbox / group # column + header **Add mentoring unit**.
- Create reuses `canCreateMentoringGroup` + `defaultMentoringUnitRoles` + `upsertMentoringGroup` (exactly 3).
- Group # click → `deleteMentoringGroup` (trio rule). Checkbox/group clicks stopPropagation so row ≥ filter stays separate.
- Verified: `npx vitest run tests/squad-ha-table.test.ts` (19 pass); `tsc --noEmit` clean.
