---
id: T085
title: HA and CA for listed players on any Career Save
status: done
priority: 1
owner: worker
claimed_at: 2026-08-16T04:05:00+02:00
started_at: 2026-08-16T04:05:00+02:00
completed_at: 2026-08-16T04:25:00+02:00
depends_on: [T084]
---

# T085 — HA and CA for listed players on any Career Save

## Why

Squad / Mentoring / Progress are the pack + CA card on **the people T084 listed**. König UID bands (`1.5e9–2.2e9`, NEWGEN floor `2.002e9`) drop everyone on a native or other-DB save. Missing attrs must be `—`, not an empty table.

## Scope

- In: person/job → UniqueID → pack blob + CA card, once each, in `extract-first-team-fast.py` (existing T014/T066 paths)
- In: UID / NEWGEN ranges are **heuristics**, not law. If save B’s people sit outside the continue-career band, follow the **person double / employment tag**, do not add that save’s UID floor as a constant
- In: UI contract unchanged: Squad HA = pack + Det/Lea from the card; Progress CA = card history; Progress HA = pack snapshots + Det/Lea from the card
- Out: new Det/Lea hunt. Favoured-club. Loans (T086). GK vs outfield Progress chrome (T087). World dump. Editing `.fm`. Committing `*.fm`

## Blind (non-negotiable)

- Do **not** git add `data/saves/` or `*.fm`. Do **not** mmap live `games/*.fm`
- Do **not** wait for another Career Save. Do **not** add a UID floor/ceiling copied from a local `.fm`
- Optional smoke on whatever `data/saves/*.fm` already exists; holes stay `—`

## Acceptance criteria

- [x] UID / NEWGEN ranges are heuristics: a listed player outside the continue-career band is **kept** (attrs `—` if blobs miss), not dropped
- [x] One pack + one CA card per listed player (no third extract). UI contract unchanged (Squad HA = pack + Det/Lea from the card)
- [x] No new save-named UID / player constants
- [x] One git commit `T085: …` on FMT/ — no `.fm` in the commit

## Notes / pointers

- `UID_LO, UID_HI = 1_500_000_000, 2_200_000_000` and `NEWGEN_UID_FLOOR` in `extract-first-team-fast.py` are continue-career observations
- Employment is still jobId → UniqueID near end of stream (`rfind`) — keep that shape
- Do not walk the CA card twice. Do not invent a third Det/Lea locus

## Progress

Shipped: job→UniqueID follows the employment tag / person double. Continue-career `UID_LO`/`UID_HI` and `NEWGEN_UID_FLOOR` rank hits and classify kind inside that band only — they no longer drop listed people. Out-of-band UniqueIDs with a person double are kept; pack + CA card are the same two loci (no third Det/Lea extract). Listed jobs with no UniqueID or missing blobs stay in the extract with attrs `None` (UI —). Kind outside the band is `UNKNOWN`.

Verified: `python -m unittest tests.test_ha_ca_any_save_t085 tests.test_unit_squads_t084 tests.test_managed_club_identity_t083 tests.test_u19_before_window_t068 tests.test_world_lists_skip_t076` (synthetic: oob+double maps; oob without double is not stolen; in-band still maps; listed job kept when uid missing; one pack + one card; miss → —). Optional local smoke counts to the human; not the recipe; no committed `.fm`.

Next: T086 (at-club vs loaned-out). Not started.
