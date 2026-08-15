---
id: T071
title: Hide cancelled Suggest on Mentoring
status: ready
priority: 3
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T069]
---

# T071 — Hide cancelled Suggest on Mentoring

## Why

Suggest is cancelled. A Suggest button on a shippable Mentoring screen looks like unfinished product. Capture via HA Group checks + Add group is the loop.

## Scope

- In: hide/remove the Suggest CTA on Mentoring
- Out: deleting Suggest code paths unless they are only the button; no new seating AI; no BMC (T070)

## Acceptance criteria

- [ ] Mentoring screen has no Suggest button
- [ ] Existing groups still show; Add group / HA Group checks still work
- [ ] One git commit `T071: …` on FMT/

## Notes / pointers

- SCOPE: Mentoring Suggest discarded
- Used loop: Group 3 = Robert + Miraglia + Itu from the table, not Suggest

## Progress

_(worker fills)_
