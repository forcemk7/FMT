---
id: T071
title: Hide cancelled Suggest on Mentoring
status: done
priority: 3
owner: cursor-worker
claimed_at: 2026-08-15T14:02:00+02:00
started_at: 2026-08-15T14:03:00+02:00
completed_at: 2026-08-15T14:08:00+02:00
depends_on: [T069]
---

# T071 — Hide cancelled Suggest on Mentoring

## Why

Suggest is cancelled. A Suggest button on a shippable Mentoring screen looks like unfinished product. Capture via HA Group checks + Add group is the loop.

## Scope

- In: hide/remove the Suggest CTA on Mentoring
- Out: deleting Suggest code paths unless they are only the button; no new seating AI; no BMC (T070)

## Acceptance criteria

- [x] Mentoring screen has no Suggest button
- [x] Existing groups still show; Add group / HA Group checks still work
- [x] One git commit `T071: …` on FMT/

## Notes / pointers

- SCOPE: Mentoring Suggest discarded
- Used loop: Group 3 = Robert + Miraglia + Itu from the table, not Suggest

## Progress

Shipped: removed Mentoring board + Add-group picker Suggest CTAs (`web/index.html`). Suggest engine left in place. Add group remains.

Verified: `npx vitest run tests/mentoring-suggest-cta.test.ts tests/mentoring-stack.test.ts tests/squad-ha-table.test.ts tests/squad-route.test.ts` — 77 passed (no Suggest button; groups persist; HA Group checks).
