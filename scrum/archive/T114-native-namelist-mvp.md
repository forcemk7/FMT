---
id: T114
title: Native MVP — clubIdAbs+488 namelist into Squad
status: done
priority: 1
owner: cursor-worker
claimed_at: "2026-08-17T01:04:00+02:00"
started_at: "2026-08-17T01:06:00+02:00"
completed_at: "2026-08-17T01:16:43+02:00"
depends_on: [T109]
---

# T114 — Native MVP — clubIdAbs+488 namelist into Squad

## Why

HQ locked a **location**, not a squad type: on native (`00950e01`), after identity club UniqueID, a **u32 count + lp32 names** sits at **clubIdAbs + 488** (five Careers: Liverpool 35, Bournemouth 33, …). Owner will compare names to FM and decide what the cluster is. Do **not** claim Senior / loans / II.

## Scope

- In: For tag `00950e01` only — after identity, read namelist at `clubIdAbs + 488` (count then length-prefixed UTF-8 names)
- In: Fill Active Squad table with those **names** (unit label e.g. `list` / `—` / `native` — not Senior). UID optional if cheap; else omit
- In: Continue / tag `02`: honest skip or empty list (no +488 assumption)
- In: Working copy + delete (T109). Synthetic test for +488 layout
- Out: Filtering to Senior. Loans. HA/CA. Claiming “Senior locked.” Fitting one save’s count as law

## Blind

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Do **not** mmap live `games/*.fm`
- Do **not** revive T108 fast extract / invent FT=25
- Do **not** label rows Senior unless owner later confirms

## Acceptance

- [x] Native + upload: Squad shows the +488 names (count matches in-file u32)
- [x] ≥2 native Careers in smoke/tests with different counts
- [x] Continue does not fake a list via +488
- [x] One commit `T114: …` on FMT/

## Notes

- Dump: `tmp/identity/t113-cluster-clubid-tie.txt`
- Replace empty T110/T111 list paths for **native** with this recipe only
- Owner next: check FM vs listed names — then HQ funds filter / object path

## Progress

- Shipped: `extract-squad-lists.py` = `native-clubid-plus488-v1` for tag `00950e01` (clubIdAbs+488 → count → lp32 names → unit `list`). Continue skips +488. UI accepts unit `list`. Synthetic UIDs (not real UniqueIDs). No Senior / T108 / HA/CA.
- Verified: unittest Liverpool 35 + Bournemouth 33 + continue skip; vitest chrome; smoke working copies gameDate1 (Liverpool 35 Alisson) + gameDate2 (Bournemouth 33) then deleted.
- Commit: recorded on FMT/ as `T114: fill Squad from native clubIdAbs+488 namelist`
