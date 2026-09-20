---
id: T162
title: Player trophy cabinet (profile desk)
status: deferred
priority: —
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: []
---

# T162 — Player trophy cabinet

## Why

Marketable profile visual: trophies won (images + counts) so winners are obvious. FM’s own history UI is clunky. Parked until Loop A (attrs / CA / HA / history) is daily habit — not sheet-replacement need-to-have.

## Scope

- In (later): bounded RE spike for a solid person → competition-wins object (live `fm.exe` path); if reliable, profile trophy desk with images + counts
- Out now: memory sweeps, UI chrome, competition pack hunting, world-table RE

## Acceptance criteria (when unfrozen)

- [ ] RE proves one squad player’s trophy list against FM (IDs + counts stable)
- [ ] Profile desk shows trophies with images + counts for mapped wins only
- [ ] No desk without a locked object

## Notes

- No trophy/honours object mapped today; Career totals = apps/goals only
- Graphics may already know a `competitions` pack path — unrelated until object lock
- Unfreeze only after Loop A stick + explicit HQ go

## HQ note (2026-09-15)

Not in FMT 1.28 — confirmed still parked. Owner flags an additional blocker beyond the object lock: the trophy graphics package needed for this would conflict with the existing logos megapack, so unfreezing this later means solving that packaging conflict too, not just the RE.
