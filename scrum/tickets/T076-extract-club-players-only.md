---
id: T076
title: Extract this club’s players — not the whole save
status: ready
priority: 4
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T069]
---

# T076 — Extract this club’s players — not the whole save

## Why

The wedge vs Genie Scout is HA/CA for **this club** without loading every player, staff, and stadium. T072 already cut multi-Python on start. This ticket is: do not spend extract time on world objects the three tabs never show.

## Scope

- In: extract path used by `npm run dev` for Squad / Loans / Mentoring / Progress
- In: FT + II + U19 identity, pack HA, Det/Lea, CA; loan flag (Squad = at-club, Loans = outgoing)
- Out: staff, stadiums, full-world scouting dump, new RE rabbit holes, FM27
- Out: “make it feel fast” with no before/after on this save

## Acceptance criteria

- [ ] Squad / Loans / Mentoring / Progress still populate for the König (or current) save
- [ ] Extract no longer walks staff/stadium (or equivalent world) lists this club’s tabs do not use — note in Progress what was skipped
- [ ] One git commit `T076: …` on FMT/
- [ ] Progress records rough before/after duration on the same save (human-run ok)

## Notes / pointers

- Never mmap live `games/*.fm`
- T068 U19 before-name list and FT CA strip stay
- If already skipped, ticket is: prove it in Progress and stop — do not invent a second extractor

## Progress

_(worker fills)_
