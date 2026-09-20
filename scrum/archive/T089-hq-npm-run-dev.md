---
id: T089
title: npm run dev from HQ workspace root
status: cancelled
priority: 1
owner: null
claimed_at: null
started_at: null
completed_at: 2026-08-16
depends_on: []
---

# T089 — cancelled: do not run FMT from HQ

HQ `Projects/` is the gatekeeper workspace, not the app. `npm run dev` belongs in `FMT/`. Do not add a root `package.json` that prefixes into FMT.
