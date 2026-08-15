---
id: T024
title: Suggest — require real influence; ban net-negative Low seat
status: cancelled
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T025]
---

# T024 — CANCELLED

Suggest is not the product (2026-08-13 HQ). Shipped-into-T025 historically; do not pick.

# T024 — Suggest: require real influence; ban net-negative Low seat

## Why

Attr-only floor when **no manual influence labels** exist. **Merged into T025 worker path** — implement thresholds as fallback inside T025; keep this ticket for test coverage of pure-attr case only if T025 splits work.

## Scope

- In: raise floor so Suggest never returns a group unless **High→Low and Mid→Low** both have at least **light** influence when no manual edges override
- In: reject groups where the **Low seat** would net-negative-influence either senior on protected attrs (Det emphasized)
- Out: duplicate manual-influence work (T025)

## Acceptance criteria

- [ ] Covered by T025 tests for unlabeled pool, or worker marks done here with shared implementation

## Progress

_(defer to T025 unless split)_
