---
id: T111
title: Senior Squad — club → squad object → player ids
status: done
priority: 1
owner: auto
claimed_at: "2026-08-16T23:24:00+02:00"
started_at: "2026-08-16T23:25:00+02:00"
completed_at: "2026-08-16T23:56:00+02:00"
depends_on: [T109]
---

# T111 — Senior Squad — club → squad object → player ids

## Why

T108/T110 cancelled: fitted / offset namelists, wrong counts, UI under-renders. Owner: treat squads as **separate** (as FM does). Lock **Senior Squad** only — mentoring core. Reserves / U21 / U19 later (vertical) or Loans → Mentoring → Progress (horizontal) — HQ chooses after Senior is honest.

## Terminology (discover in-save; do not invent)

Prefer **native strings** attached to squad objects (examples to look for, not hardcode as law):

- Senior Squad
- Reserve Squad / U21 Squad
- U19 / U18 Squad

This ticket: **Senior Squad** of the **main club** (not affiliate). Label the unit from the save’s own name when found.

## Extract path (required shape)

```
managed club UniqueID (identity, locked)
  → squad object(s) attached to that club (fixed structural links — not ~±N bytes)
  → pick Senior Squad object
  → player UniqueIDs on that squad
  → resolve display names
```

- Prefer **object graph** (pointers / typed records / club→team attachments) over sliding namelist windows
- Prove on **native FM26** first (≥2 Careers). Continue later
- UI: one list — **name**, **player uid**, squad label (Senior). No HA/CA. No Res/U19 rows in this ticket
- Counts must be owner-checkable against FM Senior Squad for the smoke save — **do not** invent FT=25

## Out

- Reserve / U19 extract. Loans. HA/CA. Mentoring. Progress. T110 namelist ~+520. `extract-first-team-fast` revival

## Blind

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Do **not** mmap live `games/*.fm` (T109)
- Do **not** hard-wire one Career’s count or offsets as law
- Do **not** claim lock from a single save or from UI showing 2 of N

## Acceptance criteria

- [x] Documented object path: club id → Senior squad object → player ids → names
- [x] Native FM26: ≥2 Careers; Senior list matches owner smoke on at least one named save (or honest miss with dump — not a fake count)
- [x] Squad table shows those rows (name + uid + Senior); no HA/CA required
- [x] One git commit `T111: …` on FMT/

## Notes

- Identity stays T099/T106. Working copy T109
- Owner smoke file: `gameDate1.fm` (Liverpool) — agent’s 25 was false; re-check real Senior count in FM before claiming lock

## Progress

### Shipped

- Replaced T110 namelist extract with `senior-squad-object-v1`: identity → club-object join (`resolve_ft_squad` PRE_NAME/teamId/7f02) → job → uid → name; unit label Senior when rows exist.
- Native `gameDate1` (Liverpool) + `gameDate2` (Bournemouth): honest miss `senior-squad-object-miss` (0 catalog team objects / 0 jobs). Dumps under `tmp/identity/t111-senior-miss-*.json` (gitignored). No invented FT=25.
- Dig notes (not shipped as law): clubIdAbs+488 namelist exists on ≥4 Careers but is T110-class / owner-rejected; no in-save `Senior Squad` string; native PRE_NAME join empty.
- UI: Squad columns include Name, UID, Unit (`Senior` supported); HA not required (null → —). Add-filter default stays FT (T044).
- Tests: `tests/test_senior_squad_object_path_t111.py`, `tests/t111-senior-squad-object-path.test.ts`; removed T110 namelist tests.

### Verified

- `python -m unittest tests.test_senior_squad_object_path_t111`
- `npx vitest run tests/t111-senior-squad-object-path.test.ts tests/squad-ha-table.test.ts`
- Live smoke: gameDate1 + gameDate2 → 0 Senior players + miss dump

### Residual risk

- Senior roster still empty until a real native club→squad object attachment is locked (continue PRE_NAME/7f02 may work later; not claimed here). Owner must confirm FM Senior count before any future lock.

### Commit

`778627554acc0b03a03c2cc29a9658db4525d05d`
