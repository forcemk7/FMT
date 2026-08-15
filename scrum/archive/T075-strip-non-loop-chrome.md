---
id: T075
title: Strip chrome that is not Squad / Loans / Mentoring / Progress
status: done
priority: 3
owner: cursor-worker
claimed_at: 2026-08-15
started_at: 2026-08-15
completed_at: 2026-08-15
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

- [x] `npm run dev` squad UI only offers Squad, Loans, Mentoring, Progress (that order)
- [x] Squad click → filter → Group capture still works
- [x] Loans tab still lists outgoing loans
- [x] One git commit `T075: …` on FMT/

## Notes / pointers

- Static HAS Pages is not this ticket unless linked from the squad app
- Do not delete `src/domain` HAS scoring if Squad still shows HAS

## Progress

Shipped: Ranker / Best Personalities nav gone; `#rank` / `#checker` / `#compare` land on Squad. Tab order is Squad | Loans | Mentoring | Progress. Ranker HTML stays hidden so Squad HAS math is unchanged. Loans pane unchanged.

Verified: `npx vitest run tests/squad-chrome-t075.test.ts tests/squad-route.test.ts tests/squad-ha-table.test.ts tests/loans-roster.test.ts tests/mentoring-suggest-cta.test.ts` — 77 passed. `npm run dev` König: four tabs; Group checks + HAS column; Loans lists outgoing FT/II/U19.
