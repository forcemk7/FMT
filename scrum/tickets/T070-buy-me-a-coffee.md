---
id: T070
title: Buy Me a Coffee tip on the UI
status: ready
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
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

- [ ] Link is visible without hunting
- [ ] Click opens Buy Me a Coffee (not a fake button)
- [ ] HA table, filters, and mentoring capture work with no payment
- [ ] One git commit `T070: …` on FMT/

## Blockers

Need the live BMC URL (e.g. `https://buymeacoffee.com/yourname`). Until STATUS Blockers has it, set this ticket `blocked`.

## Notes / pointers

- Steal: Genie Scout donate — tip on a free tool
- Do not name the Stripe product “support development” inside FMT

## Progress

_(worker fills)_
