---
id: T101
title: Save cards lock identity — FM24/FM26, continue date, update-same-name
status: done
priority: 1
owner: composer
claimed_at: 2026-08-16T12:50:00+02:00
started_at: 2026-08-16T12:51:00+02:00
completed_at: 2026-08-16T13:05:00+02:00
depends_on: [T100]
---

# T101 — Save cards lock identity — FM24/FM26, continue date, update-same-name

## Why

Native FM26 club + gameDate is locked (T099, eight saves). Continue (tag `00950e02`) still shows `—` because UniqueID+4/+6 is the native recipe. Owner has one continue Schalke; NG Regens–class switch is the **tag we already parse**. Cards must show every identity field. Update must mean **same filename**, not overwrite a different Career.

Page shell (Squad tabs) is **not** this ticket.

## Scope

- In: Persist identity marker from `tagHex`: `00950e01` → **FM26**, `00950e02` → **FM24**. Pill, fixed width
- In: **Date:** tag `01` stays T099 UniqueID+4/+6. Tag `02` uses the old continue calendar (`c708` / today_ptr — already in `extract-managed-team.py` `collect_date_candidates` / `extract-first-team-fast.py` `discover_game_date`). Do not run T099 on tag `02`. Unsure → `—`
- In: Card two rows, menu **wider** so long club names fit:

```
{FM26|FM24 pill}{club_name}                    Uploaded: {Mon DD, HH:MM AM/PM}
ID: {club_id}  Game Date: {Mon DD, YYYY}       {update icon}{delete icon}
```

- In: **Update** = refresh icon (not pencil). File picker; extract only if `file.name` matches the slot `saveName` (case-insensitive). Mismatch → refuse, do not overwrite. Different Career → user hits **+**. Delete unchanged
- Out: App header / Squad-Loans-Mentoring-Progress shell. Disk auto-sync. Squad extract. Changing T099 for tag `01`. Hardcoding König’s date. T087. `*.fm` in git

## Blind (non-negotiable)

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Do **not** mmap live `games/*.fm`
- Do **not** copy a continue save’s offsets/date into source as law — tag `02` + existing calendar functions

## Acceptance criteria

- [ ] Native tag `01` still T099 dates (synthetic UniqueID+4/+6)
- [ ] Continue tag `02` synthetic with calendar prelude/today_ptr yields that gameDate, not UniqueID-tail
- [ ] Cards show pill FM26/FM24, club name, Uploaded:, ID:, Game Date:, update icon, delete icon
- [ ] Update with a different `.fm` filename does not replace the slot
- [ ] Menu is wider than T100 (long club names visible)
- [ ] One git commit `T101: …` on FMT/ — no `.fm`

## Notes / pointers

- `HUMAN_TAGS` in `extract-managed-team.py`; persist `tagHex` or `saveLayout` on `StoredRoster`
- T100 pencil → update icon; `syncRosterSavesMenu`; `.roster-saves-menu` width
- Owner smoke: continue Schalke should get a Game Date (or honest `—`), pill **FM24**; native cards **FM26**

## Progress

Shipped: persist `tagHex` (`00950e01` → FM26 pill, `00950e02` → FM24 pill, fixed width). Date: tag 01 stays T099 UniqueID+4/+6; tag 02 uses continue calendar (`c708` / today_ptr), never UniqueID-tail; unsure → —. Cards: `{pill}{club_name}` | `Uploaded: {Mon DD, H:MM AM/PM}`; `ID:` + `Game Date:` | refresh update + delete. Menu 36/44rem. Update refuses when `file.name` ≠ slot `saveName` (case-insensitive); different Career → +. Auto-sync stays dead. No committed `.fm` / `tmp/`.

Verified: `python -m unittest` t101 + t099 + t096 + t097 (20 passed). `npx vitest run` t101 + t100 + t097 + t095 + t096 + roster-store-ingest + t088 (32 passed).

Restart `npm run dev`. Continue Schalke → FM24 + Game Date or honest `—`. Native cards → FM26. Update with another `.fm` name must refuse.
