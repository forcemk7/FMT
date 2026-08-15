---
id: T073
title: Rename Personalities tab to Squad
status: ready
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T069]
---

# T073 — Rename Personalities tab to Squad

## Why

The HA table is the at-club **squad** (youth development + mentoring), not a “personalities product.” Ship chrome: **Squad**.

## Scope

- In: user-visible tab/label Personalities → Squad (navigator, titles, empty states)
- Out: renaming every internal `personality` field; extract; Loans; Mentoring; Progress

## Acceptance criteria

- [ ] Navigator shows **Squad** where it showed Personalities
- [ ] Click/filter/Group capture still work
- [ ] One git commit `T073: …` on FMT/

## Progress

_(worker fills)_
