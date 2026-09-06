---
id: T256
title: Loan honesty — do not suppress feeder destination loans
status: done
priority: 1
owner: auto
claimed_at: "2026-09-07T00:08:00+02:00"
started_at: "2026-09-07T00:08:00+02:00"
completed_at: "2026-09-07T00:13:00+02:00"
depends_on: []
---

# T256 — Loan honesty — do not suppress feeder destination loans

## Why

U19 (and other) players **already on loan** to feeder / Normal affiliates still show as at-club on Under N. Loans desk and roster honesty miss them.

## Root cause (investigated)

`is_outgoing_external_loan` returns **false** when `loan_club_uid` is in `affiliate_reserve_club_uids`.

That set was built as **every** discovered affiliate UID — including `0x01`/`0x03` feeders after ME roster load.

## Scope

- In: Restrict the “not outgoing” UID set to **Squad-tab II / satellite** clubs only
- In: Unit test: loan to feeder UID → outgoing; loan to II UID → still internal
- In: recipes.md one-liner
- Out: New loan RE; person_loan_offset; ME opportunity rules

## Acceptance

- [x] U19 player with loan club = feeder (0x01/0x03) → `loanedOut: true` (logic)
- [x] Loan club = managed II (0x08) → still not outgoing external (T212)
- [x] Commit `T256: …`

## Progress

- Shipped: `loan_honesty_internal_reserve_uids` — keep `0x08` + type-less satellite; exclude feeders + ME-only
- Verified: `cargo test --lib loan_honesty` ok
- recipes.md updated
- Commit: (this ticket)
