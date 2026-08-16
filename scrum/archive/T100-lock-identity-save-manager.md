---
id: T100
title: Lock identity upload; last + is Active; compact save cards
status: done
priority: 1
owner: composer
claimed_at: 2026-08-16T12:04:00+02:00
started_at: 2026-08-16T12:08:00+02:00
completed_at: 2026-08-16T12:15:00+02:00
depends_on: [T099]
---

# T100 — Lock identity upload; last + is Active; compact save cards

## Why

Owner confirmed **eight** Careers: club name + UniqueID + in-game date match FM (T099). Freeze that extract. Manage saves still keeps the **first** upload Active (`upsertRoster` `keepActive` from T088). Cards still use a wide DELETE and hide uploaded time.

## Scope

- In: **Lock extract** — `+` / Edit stay identity-only (`extract-managed-team.py`: clubId, clubName, gameDate via UniqueID+4 `u16` doy / UniqueID+6 `u16` year). Do **not** edit that parser. Do **not** run FT/HA/loans. Auto-sync stays dead
- In: After a successful **+** (or Edit replace), that save is **Active**. `keepActive` must not pin the first upload
- In: Card, two rows:

```
{club_name} {club_id}          {uploaded_date}
{game_date}                    {edit icon}{delete icon}
```

Active badge stays on the Active row. Click row still selects Active. Uploaded = existing `extractedAt`
- In: **Edit** = file picker, identity-only extract into **that** slot (not SI `games/` sync)
- Out: Changing T099 date math. Restoring poll/SSE/Update-from-disk. Squad extract. T087. Dump files. `*.fm` in git

## Blind (non-negotiable)

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Do **not** mmap live `games/*.fm`

## Acceptance criteria

- [x] New `+` upload becomes Active (first save is no longer stuck Active)
- [x] Cards match the two-row layout; DELETE text button gone; edit + delete are icons under uploaded date
- [x] Extract Python date/identity code is unchanged in this commit (web/store/css only, plus tests)
- [x] Vitest: new upsert/Active + chrome layout guards
- [x] One git commit `T100: …` on FMT/ — no `.fm`

## Notes / pointers

- `web/roster-store.ts` `upsertRoster` `keepActive` — T088; identity `+` must set Active to the new `saveName`
- `web/main.ts` `syncRosterSavesMenu`; `extractedAt` already on the entry
- T088 tests that “never set Active to upserted save” must change for **new** `+` uploads only

## Progress

Shipped: `upsertRoster(..., { setActive: true })` on + / Edit persist so that save is Active. Default upsert still keepActive (T088 disk bind). Cards are two rows: club name+id | uploaded (`extractedAt`); game date | edit + delete icons. DELETE text gone. Edit opens identity file picker into that slot. Auto-sync stays dead. `extract-managed-team.py` / T099 date math untouched.

Verified: `npx vitest run` t100 + roster-store-ingest + t088 + t095 + t096 + t097 (28 passed). No committed `.fm` / `tmp/`.

Restart `npm run dev`. + a second Career Save — it must become Active. Cards: uploaded date top-right; pencil/trash under it.
