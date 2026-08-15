---
id: T075
title: Strip chrome that is not Squad / Loans / Mentoring / Progress
status: ready
priority: 3
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T069, T073, T071]
---

# T075 — Strip chrome that is not Squad / Loans / Mentoring / Progress

## Why

Ship is four tabs. Ranker / checker / compare / Suggest chrome is a second product.

## Scope

- In: remove navigator/entry points that are not Squad, Loans, Mentoring, Progress (and BMC when T070 exists)
- In: hide dead buttons (Suggest is T071)
- Out: deleting Loans; rewriting extract; deleting HA math used by Squad

## Acceptance criteria

- [ ] `npm run dev` squad UI only offers Squad, Loans, Mentoring, Progress (that order)
- [ ] Squad click → filter → Group capture still works
- [ ] Loans tab still lists outgoing loans
- [ ] One git commit `T075: …` on FMT/

## Notes / pointers

- Static HAS Pages is not this ticket unless linked from the squad app
- Do not delete `src/domain` HAS scoring if Squad still shows HAS

## Progress

_(worker fills)_
