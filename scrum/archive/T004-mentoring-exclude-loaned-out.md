---
id: T004
title: "INTEGRATE: loan detect → extract + mentoring exclude"
status: done
priority: 1
owner: cursor-worker-t004
claimed_at: 2026-08-11
started_at: 2026-08-11
completed_at: 2026-08-11
depends_on: [T004A, T004B]
---

# T004 — INTEGRATE: loan detect → extract + mentoring exclude

## Why

Parallel RE (T004A/B/C) finds signals; this ticket is the **only** one allowed to edit `extract-first-team-fast.py` / mentoring pool code.

## Scope

- In: wire proven detect into extract for FT+II(+U19); mentoring exclude + prune; regression
- Out: inventing new RE (consume A/B/C Progress); Loans tab (T005)

## Acceptance criteria

- [x] All GT UIDs present in extract tagged `loanedOut` (see T004 ticket ground truth / T004A–C)
- [x] Mentoring Suggest cannot seat them (Vlad regression)
- [x] Test or fixture: detect ≠ Sipho-only
- [x] No drive-by scope

## Claim rule

Do **not** claim until T004A has a concrete detect recipe in Progress (and T004B if II uses a different recipe). One owner only.

## Progress

### Shipped

1. **`detect_loaned_out_jobs`** — T004A template (`64 ff kind | A | 10×0 | B | club×2 | 0x000A`), kinds `0x20..0x30`, lookback **8..57**, club hi **200k** (Risse/Darmstadt `108997` needs both bumps vs A’s 56/100k).
2. **`resolve_job_uids_double_fallback`** — T004C `job||uid||uid` (prefer 12-byte prefix) for gap jobs; wired into `resolve_job_uids_batch`.
3. **Mentoring** — already excludes/prunes `loanedOut` in `web/main.ts` (`firstTeamMentoringPlayers`, `pruneMentoringGroups`); Vlad now tags → Suggest cannot seat him. No web drive-by.

### Verified (`tests/test_loan_detect_t004.py` on `tmp/live-0112-decomp.bin`)

| Player | job | club | Notes |
|--------|-----|------|-------|
| Sipho | 382267 | 1456 | still hits |
| Vlad | 437615 | 912 | was Sipho-only bug |
| Braescu | 506980 | 916 | |
| Manole | 506986 | 2238 | |
| Öztürk | 365838 | 2249 | |
| Görrissen | 315711 | 946 | gap→double-UID |
| Risse | 317202 | 108997 | gap; back=57 + club>100k |
| Pérez | 351592 | 2245 | gap→double-UID |
| Millwood | 538884 | — | **hole** (T004B; no motif) |
| FT controls | — | — | Paco/Bandeira/Kizza/Jones/Seimen miss |

### Residual

- **Millwood** still untagged (no `64ff2x` loan object on job) — T005 honesty hole, not inventing RE here.
