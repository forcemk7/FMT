---
id: T245
title: Lock Players-Go-On-Loan affiliation byte
status: blocked
priority: 1
owner: auto
claimed_at: "2026-09-06T22:27:00+02:00"
started_at: "2026-09-06T22:27:00+02:00"
completed_at: null
depends_on: [T244]
---

# T245 — Lock Players-Go-On-Loan affiliation byte

## Why

Match experience still loads feeders without a loan agreement (Daegu, Melbourne). Need one locked byte, then a simple production read — **not** runtime name-needle diffs.

## Scope

- In: RE once — dump `club+0x118` wrapper/nested hex; diff loan-on (Legia / Sparta / KL) vs loan-off (Daegu / Melbourne); lock offset + on/off in `research/recipes.md`
- In: Production filter = read that byte only; remove T242 Schalke needle auto-diff / candidate lock from load path
- Out: ME card chrome (T244); inventing PGE string for AffiliationType `0x03`; FMLE paid Save Changes as the only method (ok as A/B evidence)

## Acceptance criteria

- [ ] recipes.md documents locked region+offset and on/off values with Schalke evidence
- [ ] Load skips feeders whose loan byte ≠ on-value
- [ ] No production runtime “find separators from club names”
- [ ] Commit `T245: …`

## Blockers

Need the new Diagnostics line after rebuild/reconnect:

`Affiliation loan-flag RE (FMLE nested Players-Go-On-Loan): …`

That line now includes wrapper/nested u8 offsets, nested bit candidates, side-ptr region counts, and per-club nestedLen samples. FMLE confirms loan terms are nested (not Main/Permanent).

## Progress

- FMLE map recorded in recipes: loan-on Legia/Sparta/KL; loan-off Daegu/Melbourne; II separate.
- Probe widened: nested 0x100, wrapper side ptrs, bit separators; warning prints offsets (not just counts).
- Still no hardcoded lock — waiting on paste of the new RE warning line.
