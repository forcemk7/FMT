---
id: T023
title: INCIDENT — restore subunits; stop FT-only extract wiping II/U19; harden sync OS errors
status: cancelled
priority: 99
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: []
---

# T023 — INCIDENT: only FT shows; sync OSError; subunits wiped

## Why

**Loop break (behavior):** App meltdown — only First Team roster; Reserves / Under 19s / Loans / Mentoring empty or unusable; sync fails with an **OS…** style error.

**Cancelled 2026-08-13 (SM):** User reports sync and data appear fine. Dynamics unpaused. **Reopen** this ticket if FT-only extract wipes II/U19 or OS sync failures return.

## Scope (if reopened)

- In: **do not clear** stored `reserves`/`u19` when a new extract returns JSON `null` for those keys
- In: serialize extracts; clear lock / settle messaging
- Out: Dynamics; Mentoring Suggest; T014

## Acceptance criteria

- [ ] Successful FT extract that fails II/U19 discovery does **not** wipe previously stored reserves/u19
- [ ] Concurrent extract storm cannot stack on the same save
- [ ] File lock / settle failure shows a clear user-facing message
- [ ] After one clean full extract: FT + Reserves + U19 + Loans + Mentoring usable
- [ ] Regression test for “null subunit must not clear previous store entry”

## Notes / pointers

- Investigation notes retained in prior STATUS / agent transcript
- Residual risk: null-subunit clear + concurrent extract still in code until reopened

## Progress

- Cancelled: user-verified green; not blocking Dynamics.
