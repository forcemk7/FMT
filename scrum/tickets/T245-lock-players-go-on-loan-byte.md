---
id: T245
title: Lock Players-Go-On-Loan affiliation byte
status: ready
priority: 2
owner: null
claimed_at: null
started_at: null
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

## Progress

Ready after T244. Align: figure byte in Cursor/RE first, then ship the read.
