---
id: T004B
title: "RE: II/U19 loan signal (Manole, Braescu, Millwood, Ozturk)"
status: done
priority: 2
owner: cursor-worker-t004b
claimed_at: 2026-08-11
started_at: 2026-08-11
completed_at: 2026-08-11
depends_on: []
---

# T004B — RE: II/U19 loan signal

## Why

GT loans on II/U19 are untagged. Not Mentoring-pool blockers today, but same detect must cover them before T005 Loans tab is honest. Parallelize vs T004A (different jobs/units).

## Scope

- In: recipe for II/U19 GT loans; note if identical to T004A or different
- Out: product code edits (T004 integrate); FT Vlad (T004A); missing UIDs (T004C)

## Ground truth (in extract)

| UID | Name | Unit | jobId | FM club |
|-----|------|------|-------|---------|
| 2002390860 | Andrei Manole | II | 506986 | Augsburg |
| 2002390854 | Robert Brăescu | II | 506980 | Köln |
| 2002422274 | Ben Millwood | U19 | 538884 | SC Paderborn |
| 2002266096 | Recep Öztürk | U19 | 365838 | RW Essen |

Artifacts: same `tmp/live-0112-*` as T004A.

## Acceptance criteria

- [x] Detect recipe in Progress for ≥2 of the four (prefer all)
- [x] Spike reproduces hits; note overlap with T004A recipe
- [x] **No** product code edits

## Claim rule

One agent; do not edit files T004A is actively shaping except append-only spike outputs with distinct names (`spike-loan-ii-*`).

## Progress

### Detect recipe (handoff → T004)

Same **job-object layout as Sipho** (`64 ff 26` → Legia). Domestic II/U19 use third-byte **`0x24`** instead of **`0x26`**.

1. Motif-first: find `64 ff 24` **or** `64 ff 26`
2. Require `mm[motif-4:motif] == 00 00 00 00` (drops most at-club `64 ff 24` noise)
3. Look back **8..49** for a squad `jobId`
4. Require **duplicated** `loanClubId` u32 pair at **exactly `motif+21`**
5. `50 ≤ loanClub ≤ 100000`, `loanClub ≠ parentClub` (920)

Do **not** invent a second join. Product today is `LOAN_OUT_MOTIF = 64 ff 26` only — widen kinds + add pre4 / loanRel=21 filters.

### Hits on `tmp/live-0112-decomp.bin`

| Player | Unit | jobId | kind | back | loanClub | Name lock |
|--------|------|-------|------|------|----------|-----------|
| Braescu | II | 506980 | 24 | 41 | **916** | Köln / 1. FC K ×8 |
| Manole | II | 506986 | 24 | 37 | **2238** | Augsburg / FC Augsburg ×8 |
| Öztürk | U19 | 365838 | 24 | 49 | **2249** | weak Rot-Wei×1 (shape OK) |
| Millwood | U19 | 538884 | — | — | **none** | no `64 ff 2x` loan object on any job site (back 8..80) |
| Sipho (ctrl) | FT | 382267 | 26 | 25 | 1456 | existing product hit |

### False-positive check

- `back_hi=48` + pre4 + loanRel21: **0 FP** on at-club FT/II/U19; tags Braescu+Manole+Sipho (misses Öztürk)
- `back_hi=49` + same filters: also Öztürk; also tags **Vlad→912** (Frankfurt name lock) — T004A true loan, not an at-club FP
- Controls miss: Paco, Bandeira, Kizza, Jones, Seimen

### Overlap vs T004A

**Identical recipe.** Sipho = kind `26`; Vlad/II/U19 domestic = kind `24`. One detector covers both once kinds are widened + filtered. Millwood remains a hole (no motif on job) — may need T004C-style follow-up, not a different motif family.

### Spikes / how tested

- `scripts/spike-loan-ii-u19-detect.py` → `tmp/fm-spike/spike-loan-ii-u19.txt`
- `scripts/spike-loan-ii-u19-v2.py` → filter sweeps
- `scripts/spike-loan-ii-u19-v3.py` → clubId name locks
- `scripts/spike-loan-ii-u19-confirm.py` → **RESULT PASS** (Braescu/Manole/Ozturk/Sipho + Millwood untagged + FT controls clean)

No edits to `extract-first-team-fast.py` / `web/main.ts`.
