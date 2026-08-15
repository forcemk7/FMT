---
id: T073
title: Rename Personalities tab to Squad
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-08-15T13:56:00+02:00
started_at: 2026-08-15T13:57:00+02:00
completed_at: 2026-08-15T14:00:00+02:00
depends_on: [T069]
---

# T073 — Rename Personalities tab to Squad

## Why

The HA table is the at-club **squad** (youth development + mentoring), not a “personalities product.” Ship chrome: **Squad**.

## Scope

- In: user-visible tab/label Personalities → Squad (navigator, titles, empty states)
- Out: renaming every internal `personality` field; extract; Loans; Mentoring; Progress

## Acceptance criteria

- [x] Navigator shows **Squad** where it showed Personalities
- [x] Click/filter/Group capture still work
- [x] One git commit `T073: …` on FMT/

## Progress

Shipped: navigator tab + roster lede/aria now **Squad** (`web/index.html`, `web/main.ts` tab text). Internal `personalities` unit view / hashes / Personality column unchanged.

Verified: `npx vitest run tests/squad-ha-table.test.ts tests/squad-route.test.ts` — 63 passed (click/filter/Group + `#roster` hashes). Ranker “Best Personalities” chrome left for T075.
