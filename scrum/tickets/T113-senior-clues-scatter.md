---
id: T113
title: Senior clues — broad shallow probes (any hit wins)
status: ready
priority: 1
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T112]
---

# T113 — Senior clues — broad shallow probes (any hit wins)

## Why

T112 race: UI titles absent; `squad` not after club id; `Schalke 04 II` strings exist. Owner: **broad + shallow** — many tiny experiments, any clue, not one deep rabbit hole.

## Experiments (each = short dump + plain English; stop early)

| # | Probe | Primary input | Success looks like |
|---|--------|---------------|--------------------|
| 1 | **Name → up** | `gameDate1` — find `Alisson` (and 1–2 other unique Senior names if easy) | offset + 32–64 bytes context; note any u32 that could be uid/team |
| 2 | **II name row** | `dynamics-c` — all `Schalke 04 II` hits | for 2–3 hits: ±128 hex/ascii; any count+id-list shape? |
| 3 | **Incoming club id** | `gameDate1` club **676** + `dynamics-c` **920** | how many times id appears; 5 sample contexts (plain) |
| 4 | **After club id motif** | `gameDate1` vs `gameDate2` | 64–128 bytes *after* each club UniqueID — same / different? |
| 5 | **Employment / job crumbs** | same two saves | any obvious repeated tag near club id or near Alisson (document; no full join) |
| 6 | **Rolling pack** | only if König `FM24Career (v0x)` still on disk | else STATUS: skipped — deleted |

Out: full Senior list lock; HA/CA; EXE RE; claiming “pattern locked.”

## Blind

- No `*.fm` / `tmp/` in git; no live `games/*.fm`
- Each probe ≤ ~15–20 min effort; dump under `tmp/identity/t113-*.txt`
- Plain English in dump header

## Acceptance

- [ ] ≥4 probes have dumps (or explicit skip)
- [ ] One STATUS blurb listing **any** positive clues
- [ ] Commit `T113: …` only if product/script shipped; HQ race dumps alone may stay uncommitted

## Progress

**HQ scatter race (2026-08-17) — all probes done:**

| Probe | Result |
|-------|--------|
| 1 name→up | **Clue:** early hit ~22009 packs `Alisson` + `Jeremie Frimpong` + `Giovanni Leoni` together (Senior-looking). Many later “Alisson” hits are world noise. |
| 2 II rows | Catalog only: `FC Schalke 04 II` / `Schalke 04 II` length-prefixed pair — **no** player-id list on the string. |
| 3 incoming id | Club id appears often (676×97 / 920×504 in first 16MB) — many attachments exist. |
| 4 after club id | Post-UniqueID = **date tail** then shared zeros/motif — **not** the squad list. |
| 5 job crumbs | `7f02` not next to identity club id (+118KB); some near other club-id hits. Rolling pack **skipped** (deleted). |

**Best next brick:** dissect the **early name cluster** (probe 1 hit 1) as a candidate Senior list object — not T110-style “count all names near identity.”
