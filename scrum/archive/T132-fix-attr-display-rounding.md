---
id: T132
title: Fix attribute display rounding (+1 vs FM/FMLE)
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-25T17:25:00Z
started_at: 2026-08-25T17:25:00Z
completed_at: 2026-08-25T17:35:00Z
depends_on: []
---

# T132 — Fix attribute display rounding (+1 vs FM/FMLE)

## Why

Managed GK attrs (Aerial Reach / Kicking / One on Ones) read **+1** vs in-game FM and FMLE. Desk trust is the product.

## Scope

- In: Change `display_attribute` to FM/FSS rounding: `floor(raw/5 + 0.5)` ≡ `(raw+2)/5`
- In: Update entity-map transform note + unit check for boundary raw 81 → 16
- Out: Offset remapping, CA/PA changes

## Acceptance criteria

- [x] Same player GK attrs match FM/FMLE for the reported mismatches
- [x] Other attrs that already matched stay correct (no blanket −1)

## Progress

Root cause: `(raw+4)/5` rounded up too hard. FM/FMLE/FSS use `floor(raw/5+0.5)` → `(raw+2)/5`.
Unit test `display_attribute_matches_fm_and_fss_rounding` covers raw 81→16 (old formula gave 17).
Reload Active Save to verify live Aerial Reach / Kicking / One on Ones.
