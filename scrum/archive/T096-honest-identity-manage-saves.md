---
id: T096
title: Honest club id, name, and game date on Manage saves
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-16
started_at: 2026-08-16
completed_at: 2026-08-16
depends_on: [T083]
---

# T096 — Honest club id, name, and game date on Manage saves

## Why

Step 1 of the extract ladder. Manage saves must show **club UniqueID**, **club name**, and **in-game date** that match FM for **any** Career Save. Leicester printed **May 25, 2038**; the owner says that date is wrong. Club line can look right while the calendar is a König-fitted guess (`discover_game_date`: first 24MB, `c708` prelude, latest `today_ptr` / calendar-run end, years 2020–2050). A wrong date is worse than `—`. If these three fields cannot be honest without fitting one save, stop — do not start squad lists.

## Scope

- In: **Dump this file** (untracked, already on disk): `data/saves/convert_to_human_readable_report.fm` (~60MB). Decompress zstd, write a **readable report** the owner can open: `tmp/identity/convert_to_human_readable_report.txt` (gitignored). Include identity tag/offset, club id/name, **date candidates** (iso, days-from-1900, offset, nearby bytes), hex + printable strings around the identity hit. Not a full-world `.txt` of the blob
- In: **Upload / +** on a Career Save extracts **only meta** this ticket: `clubId`, `clubName`, `gameDate`. Persist those on the Manage saves row. Do **not** run FT/II/U19, names, HA/CA, or loans on upload
- In: date recipe is structural from the identity neighborhood. Do **not** pick “latest calendar table in the first 24MB”. If unsure, `gameDate` is null / row shows `—`, and the dump still lists candidates
- In: continue (König) still prints club id/name if that save is uploaded for meta; date stays honest or `—` — do not keep 2038/2040 as law
- Out: Squad table fill. HA/CA. Loans. T087. www. Committing `*.fm`, decompressed blobs, or `tmp/` dumps. Live `games/*.fm`. New MB/offset/club constants from Leicester or König

## Blind (non-negotiable)

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`, faces, logos
- Do **not** mmap live `Documents/Sports Interactive/…/games/*.fm`
- Do **not** copy Leicester/König dates, UniqueIDs, or offsets into source as law
- Required smoke: `data/saves/convert_to_human_readable_report.fm` → `tmp/identity/convert_to_human_readable_report.txt`. Tell the human that path. Truncated `.fm` is not a pass

## Acceptance criteria

- [x] `tmp/identity/convert_to_human_readable_report.txt` exists after the worker run (gitignored). Owner can open it. Contains club id, club name, identity offset/tag, date candidates, hex+strings around identity
- [x] **+ / upload** of a `.fm` extracts **only** clubId, clubName, gameDate into the Manage saves row — no squad walk, no 2GB HA extract
- [x] Manage saves row **In-game** is that extract `gameDate`, or `—` if unset — never a confident wrong year from the 24MB calendar-run heuristic
- [x] Synthetic: identity tags still parse (T083). Synthetic blob with two calendar dates (a table date later than “today” near identity) must not pick the table date
- [x] Continue identity still resolves club id/name (no Schalke NameError / empty club line)
- [x] One git commit `T096: …` on FMT/ — no `.fm`, no `tmp/` dump, no decompressed world in the commit

## Notes / pointers

- `.fm` is zstd + binary, not text. Full decompress to “the whole save as text” is hundreds of MB of noise. `tmp/` is already gitignored. Dump **neighborhood + candidates**, not the world
- `extract-managed-team.py` already has `tmp/calib/early-last.bin` — same idea, make it owner-readable
- `discover_game_date` in `extract-first-team-fast.py`: `GAME_DATE_PRELUDE` `c708000000`, `GAME_DATE_EARLY` 24MB, `today_ptr_latest` / `calendar_run_end`. That is the 2038 lie
- Dropdown: `web/main.ts` `syncRosterSavesMenu` club line + `formatInGameDateRow(entry.gameDate)`
- Filename `In-game date DD.MM.YYYY` is not a source (T064)
- Squad join is **not** this ticket. Next ladder step only if the owner says the three fields match FM

## Progress

Shipped: + / upload runs `extract-managed-team.py` (clubId, clubName, gameDate only — no FT/II/U19/HA/loans). Date is identity-neighborhood today_ptr, never the 24MB calendar-run. Unsure → `gameDate` null / In-game `—`. Disk GET still full extract, but that path also stopped persisting the calendar-run year.

Dump (gitignored): `tmp/identity/convert_to_human_readable_report.txt` — Liverpool **676**, tag `00950e01` @ 21486, gameDate **—** (no prelude/today_ptr in ±64KB; u16 after UniqueID includes year 2026, not picked).

Verified: `python -m unittest tests.test_identity_game_date_t096 tests.test_managed_club_identity_t083` (11). `npx vitest run tests/t096-honest-identity-manage-saves.test.ts tests/t095-add-delete-save-while-syncing.test.ts` (6). Local dump of `data/saves/convert_to_human_readable_report.fm`. No committed `.fm` / `tmp/`.

Restart `npm run dev` and **+** a Career Save. Owner: say whether club id, name, and In-game match FM before any squad-list ticket.
