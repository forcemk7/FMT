---
id: T004C
title: "RE: missing loan UIDs in extract (Risse, Perez, Gorrissen)"
status: done
priority: 3
owner: cursor-worker-t004c
claimed_at: 2026-08-11
started_at: 2026-08-11
completed_at: 2026-08-11
depends_on: []
---

# T004C — RE: missing loan UIDs in extract

## Why

FM loan list includes players **absent** from FT/II/U19 extract. Blocks complete loan tagging and T005. Görrissen near FT gap job `315711`.

## Scope

- In: resolve how to attach these UIDs to a squad unit + job (or document why gap jobs cannot resolve); recipe for extract follow-up
- Out: product wiring (T004); domestic motif for Vlad (T004A) unless found incidentally

## Ground truth (missing from extract)

| UID | Name | FM club | Notes |
|-----|------|---------|-------|
| 2002217460 | Landri Risse | Darmstadt | no emp jobs found earlier |
| 2002251850 | Miguel Pérez | Kiel | no emp jobs found earlier |
| 2002215969 | Lion Görrissen | St. Pauli | near gap job `315711` |

FT list gaps on 01.12.2039: `215122`, `382374`, `315711` (header 33 / resolved 30).

## Acceptance criteria

- [x] Each UID: linked jobId / unit / or proven unlinkable with evidence
- [x] Progress states what extract change T004 would need (if any)
- [x] **No** product code edits unless explicitly expanding extract discovery — prefer recipe only

## Claim rule

One agent; spike names `spike-loan-missing-*`.

## Progress

### Detect recipe (live-0112)

Gap jobs have **zero** standard emp hits (`<tag> 02 <job> 02 <uid>`). Fallback:

```
pack_u32(jobId) || pack_u32(uid) || pack_u32(uid)   # double-UID right after job
# optional prefix: 00 00 00 00 08 02 40 30 04 00 00 00
```

| UID | Name | Unit | jobId |
|-----|------|------|-------|
| 2002215969 | Lion Görrissen | FT | 315711 (double@259021637) |
| 2002217460 | Landri Risse | II | 317202 (double@260209359) |
| 2002251850 | Miguel Pérez | II | 351592 (double@275679068) |

Also resolves non-GT FT gaps: `215122→2002115380`, `382374→2002282632`.

List layout note: FT jobs at `listAbs+4*i` (no u16 prefix); II jobs at `listAbs+2+4*i`.

### What T004 extract needs

1. On emp-resolve miss for a squad-list job → double-UID fallback above.
2. Honour FT vs II/U19 list layouts.
3. Then run loan motif on the new jobIds (T004A/B).

### How tested

- `tmp/live-0112-decomp.bin` + `tmp/live-0112-extract.json`
- Spike: `scripts/spike-loan-missing-uids.py` + confirmation scan
- Recipe file: `tmp/fm-spike/loan-missing-uids-recipe.txt`
- No product edits.
