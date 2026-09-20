---
id: T110
title: First-principles squad lists — native FM26 first
status: cancelled
priority: 1
owner: auto
claimed_at: "2026-08-16T22:15:00+02:00"
started_at: "2026-08-16T22:16:00+02:00"
completed_at: "2026-08-16T22:53:54+02:00"
cancelled_at: "2026-08-16T23:20:00+02:00"
depends_on: [T109]
---

# T110 — CANCELLED (owner rejected)

## Why cancelled

Agent claimed native FT namelist “locked” (identityAbs ~+520, Liverpool **25** / Bournemouth **24**). Owner: **25 is wrong** for `gameDate1.fm`; UI only rendered **2** names (Alisson, Frimpong). Recipe is neighborhood namelist / byte offset — not an object path from club → squad → player ids.

**Do not build on T110.** Next: **T111** — Senior Squad only, object path, native FM terminology.

## Progress (historical)

- `extract-squad-lists.py` namelist count → lp32 names. Rejected.
