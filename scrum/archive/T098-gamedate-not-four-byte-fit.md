---
id: T098
title: Game date is doy before year, not a 4-byte tail fit
status: cancelled
priority: 1
owner: human
claimed_at: null
started_at: null
completed_at: 2026-08-16
depends_on: [T097]
---

# T098 — Game date is doy before year, not a 4-byte tail fit

## Why

Cancelled. Four owner-dated saves showed **u16 doy + u16 year**, not u8 doy before year. Superseded by **T099**.

## Progress

Cancelled 2026-08-16 HQ: encoding was wrong. T099 is the struct.
