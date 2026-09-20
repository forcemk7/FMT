---
id: T294
title: Players Go On Loan flag doesn't generalize to affiliationType 0x01
status: blocked
priority: null
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: []
---

# T294 — Players Go On Loan flag doesn't generalize to affiliationType `0x01`

## Why

T287 locked `wrapper+0x2E` as the "Players Go On Loan" byte — confirmed correct for affiliationType `0x03` (Kaiserslautern/Legia/Sparta on the Schalke save, cross-validated against FMLE's own checkbox 7/7). Checking a second save (Barcelona) found the same byte reads *off* for Olot, an affiliationType `0x01` link, even though FMLE and the in-game text both confirm Olot's loan agreement is genuinely active. `0xFE` (the confirmed on-value for `0x03`) does not appear anywhere in Olot's full 128-byte nested or wrapper blob, ruling out a simple offset shift — whatever encodes this for `0x01` is a different mechanism.

Real bug (Olot won't get Match Experience loan-destination cards even though the agreement is active), but not actionable yet — see Blockers.

## Scope (once unblocked)

- In: Falsifiable A/B for affiliationType `0x01` specifically — at least one confirmed-on and one confirmed-off `0x01` sample (FMLE-verified, same as T287's method) on the same save
- In: Isolate whether the real variable is affiliation type (`0x01` vs `0x03`) or save provenance (FM26-native vs FM24→26-converted) — ideally by also finding a `0x03` sample on a native-FM26 save, or a second `0x01` sample on an FM24-converted save
- In: Use `probe-loan-flag`'s existing toolkit (`find_stable_u8_separators`, `find_stable_bit_separators`, `find_stable_nonzero_separators`, both nested and wrapper regions) — already generalized, just needs real on/off samples for this type
- Out: Touching the `0x03` lock (`wrapper+0x2E`, `PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET`) — that's confirmed correct, do not "fix" it while chasing this
- Out: Any other affiliation type not yet confirmed broken

## Acceptance criteria

- [ ] Olot (or an equivalent confirmed-on `0x01` sample) resolves correctly for Match Experience
- [ ] `0x03` clubs (Kaiserslautern/Legia/Sparta-equivalent) still resolve correctly — no regression
- [ ] `research/recipes.md` updated with the confirmed `0x01` byte/condition, and whichever of type-vs-provenance turned out to matter
- [ ] One commit `T294: …`

## Blockers

- **Need a second affiliationType `0x01` sample** (on or off) on some save to diff against Olot — Barcelona has exactly one `0x01` link, nothing to compare it to
- **Need either:** a native-FM26 save with a `0x03` affiliate (to check whether `wrapper+0x2E` still holds there), or an FM24→26-converted save with a second `0x01` affiliate (to check whether it's a type issue, not a provenance issue) — either would help isolate the confounded variable
- Owner: flag when a save surfaces either of the above; this ticket stays blocked until then

**New, free check surfaced by T296 (2026-09-20):** the Olot read this ticket is built on was taken while Barcelona was sitting at its exact load date with zero days ever simulated. T296 found a different field (`player_current_date_offset`) reading as broken purely because of that save-freshness, not because of native-vs-converted provenance — a third, previously uncontrolled variable in this A/B. The owner has since advanced Barcelona past its load date. Before spending effort isolating type-vs-provenance, re-read Olot's `wrapper+0x2E` on the now-advanced save (no new RE needed) — if it now reads on, this ticket may resolve for free and provenance/type were never the real variable.

## Notes / pointers

- Full writeup: `research/recipes.md`, "Open: `wrapper+0x2E` does not generalize to affiliationType `0x01`" (T287 section)
- Prior work: T287 (locked `0x03` case), T245/T286 (superseded nested+0x65 approach)
- `probe-loan-flag`'s on/off classification (`schalke_loan_on_name`/`schalke_loan_off_name`) is hardcoded to Schalke club names — will need generalizing (or a second needle set) before it's useful on a non-Schalke save's `0x03`/`0x01` mix

## Progress

_(worker fills)_
