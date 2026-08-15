---
id: T070
title: Buy Me a Coffee tip on the UI
status: done
priority: 2
owner: worker
claimed_at: 2026-08-15T15:35:00+02:00
started_at: 2026-08-15T15:36:00+02:00
completed_at: 2026-08-15T15:38:00+02:00
depends_on: [T069]
---

# T070 — Buy Me a Coffee tip on the UI

## Why

Ship money check is a tip, not a paywall. Ground truth = someone clicks Buy Me a Coffee. Table and extract stay free.

## Scope

- In: one visible BMC link (shared chrome) opening the real BMC page in a new tab
- In: copy that this is optional / thank-you, not required to use the table
- Out: Stripe, gating extract/HA behind payment, Suggest, new tabs
- Out: inventing a username — use `FMT_BMC_URL` or the URL HQ puts in STATUS Blockers

## Acceptance criteria

- [x] Link is visible without hunting
- [x] Click opens Buy Me a Coffee (not a fake button)
- [x] HA table, filters, and mentoring capture work with no payment
- [x] One git commit `T070: …` on FMT/

## Blockers

None. HQ URL: `https://buymeacoffee.com/mrramirez`

## Notes / pointers

- Steal: Genie Scout donate — tip on a free tool
- Do not name the Stripe product “support development” inside FMT
- Use exactly `https://buymeacoffee.com/mrramirez` (STATUS Blockers). Do not invent another username.

## Progress

Shipped: header `Buy me a coffee` link to `https://buymeacoffee.com/mrramirez` (`target=_blank`, `rel=noopener`). Visible copy: optional thank-you. Title: not required to use the table. No Stripe / paywall. HA table `#roster-body` and mentoring Add group unchanged.

Verified: `npx vitest run tests/bmc-tip-t070.test.ts` — 2 passed.
