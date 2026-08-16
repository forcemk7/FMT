---
id: T097
title: Bare Manage saves — no auto-sync, lock game date
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-16
started_at: 2026-08-16
completed_at: 2026-08-16
depends_on: [T096]
---

# T097 — Bare Manage saves — no auto-sync, lock game date

## Why

Rebuild from scratch. Club id and club name from T083/T096 look locked. **In-game date is still `—`.** The inspect dump already shows a **year 2026 u16 immediately after club UniqueID** — T096 refused it because it only picks `c708` today_ptr in ±64KB, and this save has none. Wrong 2038 is worse than `—`; `—` is not locked.

Separately: **any save that looks like Schalke still starts the old disk sync** (poll / SSE / startup `maybeRefreshActiveSaveFromDisk` / disk-linked Update). T096 left disk GET as full extract. That is the old product. Decouple it.

## Scope

- In: Manage saves is **bare**: **+** (identity-only meta), list (club id, club name, game date), select Active, **Delete**. Nothing else
- In: **Kill auto-sync.** No 8s poll, no SSE `save-changed`, no startup disk refresh, no Update-from-SI-`games/` , no disk-linked recopy. A Schalke-named or König-sized `.fm` must not start extracting because it is on disk
- In: **Lock gameDate** on the identity UniqueID tail. Owner-confirmed encoding: after club UniqueID `u32`, a `u16` little-endian **year**, and the **`u8` immediately before that year is day-of-year (1–366)**. `date(year, 1, 1) + (doy - 1)`. Not packed day/month (`04 04` as 4 Apr). Not 24MB `c708` calendar. Not a hardcoded club/year/day. Invalid doy/year → `—`
- In: Refresh `tmp/identity/convert_to_human_readable_report.txt` so the owner sees doy + year + iso
- Out: Squad / HA / loans extract. Restoring poll “for later”. T087. www. Committing `*.fm` or `tmp/`

## Blind (non-negotiable)

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Do **not** mmap live `games/*.fm`
- Do **not** copy club ids, years, or offsets from the inspect save into source as law

## Acceptance criteria

- [x] After `npm run dev`, no extract starts unless the owner clicks **+** (or an explicit extract control if one remains — default is none). Schalke on disk does not sync
- [x] Manage saves chrome: + , rows with club id / name / in-game date, Delete, Active. No Update-from-disk, no Syncing-from-poll
- [x] **+** still identity-only (clubId, clubName, gameDate)
- [x] Inspect save / native upload: **gameDate is doy-before-year on the UniqueID tail**, matching FM (not `—`, not 4 Apr from `04 04` as day/month, not 2038-from-table)
- [x] Synthetic: UniqueID then `u8` + `u8 doy` + `u16 year` → that calendar day; a later calendar-table date in the blob is not picked; `04 04 ea 07` with doy 4 / year 2026 is **4 Jan**, not 4 Apr
- [x] Dump refreshed at `tmp/identity/convert_to_human_readable_report.txt`
- [x] One git commit `T097: …` on FMT/ — no `.fm`, no `tmp/`

## Notes / pointers

- Date encoding (owner, 2026-08-16): UniqueID `u32` then bytes; **`u8` doy immediately before `u16` LE year**. Inspect tail `04 04 ea 07` → doy 4, year 2026 → **4 Jan 2026** (matches FM). Do not treat `04 04` as day+month (that would be 4 Apr). The first `04` may be a separate field; doy is the byte **against** the year. Do not copy that iso into source as law — copy the struct
- Dump: `tmp/identity/convert_to_human_readable_report.txt`
- `web/main.ts`: `maybeRefreshActiveSaveFromDisk`, `savePollTimer` 8000, `EventSource` `/api/roster/events`
- T096: `pick_game_date_near_identity` — replace with UniqueID-tail doy+year; do not revive `GAME_DATE_EARLY` 24MB

## Progress

Shipped: Manage saves is bare (+, club id/name, in-game date, Active, Delete). Auto-sync killed (no 8s poll, no SSE, no startup disk refresh, no Update-from-games, GET disk extract 405). gameDate is UniqueID-tail `u8` doy immediately before `u16` LE year (`date(year,1,1)+(doy-1)`). Invalid → —. Not day/month, not 24MB calendar.

Dump (gitignored): `tmp/identity/convert_to_human_readable_report.txt` — doy 4, year 2026, iso 2026-01-04, tailHex 0404ea07.

Verified: `python -m unittest tests.test_identity_game_date_t097 tests.test_identity_game_date_t096 tests.test_managed_club_identity_t083` (17). `npx vitest run` (281). Inspect save extract `gameDate=2026-01-04`. No committed `.fm` / `tmp/`.

Restart `npm run dev` and **+** a Career Save. Owner: say whether In-game matches FM. Schalke on disk must not start extracting.
