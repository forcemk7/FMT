---
id: T080
title: Stop favoured-club extract on roster path
status: blocked
priority: 3
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T086]
---

# T080 — Stop favoured-club extract on roster path

## Why

Favoured-club was an intended feature and was dropped. Roster extract still runs `extract-favoured-scouts.py` after First Team — a second full zstd + ~2GB temp. Nothing on Squad / Loans / Mentoring / Progress shows it. That wait is leftover.

## Scope

- In: `/api/roster/first-team` (and the same Vite extract used by upload / auto-sync) must **not** spawn favoured-scout Python
- In: `/api/scout/favoured-club` must not start a decompress (404 or gone)
- Out: new scout UI, deleting every spike script, rewriting `history.json` schema (unread `favouredClub` keys may stay)
- Out: T077 host, loan-scan speed (T081), live `games/*.fm`

## Acceptance criteria

- [ ] One roster extract = one Python (`extract-first-team-fast.py` only)
- [ ] Squad / Loans / Mentoring / Progress still populate from that extract
- [ ] Progress line / NDJSON no longer waits on “Scanning favoured-club…”
- [ ] One git commit `T080: …` on FMT/

## Notes / pointers

- `vite.config.ts` `runExtractStreaming` → `extractFavouredClubScouts`
- `shared/save/extract-favoured-scouts.ts` / `scripts/extract-favoured-scouts.py`
- T072 lock stays for the one remaining extract
- Never mmap live `Sports Interactive/games/*.fm`

## Progress

_(worker fills)_
