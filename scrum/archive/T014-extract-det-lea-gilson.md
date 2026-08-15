---
id: T014
title: Gilson Det/Lea on HA table — tip unlock for ≥ filter
status: done
priority: 1
owner: auto
claimed_at: "2026-08-13T20:28:00+02:00"
started_at: "2026-08-13T20:29:30+02:00"
completed_at: "2026-08-13T21:08:02+02:00"
depends_on: [T013, T033]
---

# T014 — Det/Lea for Gilson-class so ≥ filter is honest

## Why

**Loop break:** Personalities ≥ filter uses Det/Lea. Strong-HAS players with pack but **missing Det/Lea** (hist=0 / recent signing) fail closed or cannot be judged on Det — the mentoring attr users actually care about. Domenico Gilson was the GT case; **first training report is now in** the latest Career Save under `data/saves/`.

Prior unfunded note (“Det visible in FM”) is wrong for this product: the drill is **filter in FMT**, not glance in FM.

## Scope

- In: Re-extract **latest** Schalke save in `data/saves/` (In-game date may have moved past 31.01.2040 — use newest `.fm`)
- In: Gilson (UID `2002200653`) must expose **live Det + Lea** on the Personalities HA table (and thus in one-click ≥ floors) — prefer **Progress Report / attributeHistory tip** path now that tip exists
- In: If tip path still misses Det/Lea after extract: document why + minimal fix (do **not** invent numbers). Full-save brute force only if tip is absent or wrong vs FM GT
- In: Blind honesty — missing stays `—`; never Born Leader without Det/Lea (T013 holds)
- Out: Suggest; CA/PA columns; Dynamics; inventing Det/Lea; Mentoring UI rewrite

## Acceptance criteria

- [x] After load of latest save, Gilson row shows Det and Lea as numbers (not `—`) matching FM Personal tab GT (was Det=14 Lea=16 — **reconfirm** after tip; tip may have moved attrs)
- [x] Clicking Gilson writes Det ≥ and Lea ≥ into the ≥ preset from those extract values
- [x] At least one other previously hist=0 / tip-short teammate (if any) also gets Det/Lea from tip, or explicit note “Gilson-only tip this save”
- [x] No invented Det/Lea; poison/foreign CA decoys still rejected
- [x] Tests or fixture lock updated for tip-present Gilson path

## Notes / pointers

- Save: `data/saves/` — tip present on newest `.fm` by mtime (`dynamics-b.fm`); named `FC Schalke…31.01.2040.fm` still tip-absent
- UID `2002200653`; pack Ada14 Amb15 Loy15 Pre18 Pro16 Spo16 Tem13 Con5
- Tip card: gap 2060, snapshotU16 41360, mental Det14/Lea16, technical wiped (Technique=0)
- Fix: `_accept_first_wiped_progress_tip` — keep mental/phys when u16>0 + in-band gap; strip tech; poison u16=0 still rejected

## Progress

**Shipped:** First Progress Report tip for Gilson was present on `dynamics-b.fm` but rejected because technical was wiped and there was no prior tip to inherit from. Accept that class (u16>0 + ATTR_CARD_GAP band) so Det/Lea land on HA / ≥ preset. Reconfirmed Det=14 Lea=16 from tip mental decode. Gilson-only tip of this class this save; other hist=0 teammates stay `—`. Poison tests + T013 Born Leader gate still pass.

**Verified:** `python -m unittest tests.test_live_ca_continuity` (7 ok); `npx vitest run tests/squad-ha-table.test.ts tests/match-combo.test.ts tests/roster-personality-signals.test.ts` (36 pass). Probe on decompressed dynamics-b: Gilson hist=1 status=same Det14/Lea16.

**Residual risk:** Named Career Save file without tip still yields `—` (honest). Default extract picks newest `.fm` (dynamics-b) by mtime/size — load that save (or any post-tip continue) for Gilson Det/Lea.
