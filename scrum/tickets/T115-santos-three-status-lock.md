---
id: T115
title: Santos — lock owned-at-club / owned-out / inbound-loan by UniqueID
status: blocked
priority: 1
owner: cursor-worker
claimed_at: 2026-08-17T15:05:00Z
started_at: 2026-08-17T15:08:00Z
completed_at: null
depends_on: [T114]
---

# T115 — Santos — lock owned-at-club / owned-out / inbound-loan by UniqueID

## Why

Generic Squad extract needs three FM statuses, not a namelist count. Owner locked the meanings on **gameDate8 Santos** (native, Senior Squad Players **42** UniqueIDs). `clubIdAbs+488` is a 26-name subset — keep it as a clue, not the product list.

## Status law (owner)

| UI colour | Meaning | Tab later |
|-----------|---------|-----------|
| white | club-**owned**, **at club** | Squad |
| pink/red | club-**owned**, **on loan at other clubs** | Loans |
| blue | **not owned**, on loan **at club** | Squad (at-club); not owned |

Do not invent a fourth bucket this ticket.

## Scope

- In: Working copy of `data/saves/gameDate8.fm` only (T109 copy/delete; never live SI `games/*.fm`)
- In: From managed club, find a **structural** path to these **42 UniqueIDs** and classify each into the three statuses
- In: Dump under `tmp/identity/` (human-readable: id, name, status, file offset / object kind). Not committed
- In: Unittest (or script + unittest) that classifies the gold 42 on a working copy when the save is present; skip-or-synthetic if absent
- Out: Bodø / other Careers. Generic extractor for all saves. HA/CA. UI Senior label. Shipping Squad/Loans split in the app
- Out: Fitting `+488`, T108 fast extract, T110 FT=25, T111 “Senior object” claim
- Out: Hardcoding Santos UniqueIDs in product extract (gold belongs in **tests/fixtures**, not `extract-*.py` law)

## Blind

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`, faces, logos
- Do **not** mmap live `Documents/Sports Interactive/…/games/`
- Do **not** treat name-string match as the lock (IDs are the lock; names are labels)
- Do **not** “fix” owner’s 32 vs 42 by dropping inbound or outbound without evidence
- Residual: screenshot colours sum **28 white + 11 out + 3 in = 42**. Owner also wrote squad **32 (42)**. 28+3=31. Do not force 32. Report if a 32nd at-club id exists; otherwise note the off-by-one and still lock the 42 IDs

## Acceptance

- [ ] All **42** UniqueIDs below are found in the Santos save by **id**, not by guessing names
- [ ] Each id maps to exactly one status: `owned_at_club` | `owned_out_on_loan` | `inbound_loan`
- [ ] Classification matches the gold tables (white / pink / blue)
- [ ] Recipe is structural (club → player record / job / contract / loan object). Offset-from-one-name is a fail
- [ ] Dump written; unittest records the lock; one commit `T115: …` on `FMT/`
- [x] If blocked: dump what was tried, which ids missed, `status: blocked` — do not ship a fitted 26-name list as success

## Gold — gameDate8 Santos

Native tag `00950e01`. FM header: Senior Squad Players **(42)**.

### owned_at_club (white)

| UniqueID | Name |
|----------|------|
| 2000206937 | Rodrigo Falcão |
| 19338228 | Gabriel Brazão |
| 19399114 | Diogenes |
| 19290866 | Alex Nascimento |
| 14177869 | Adonis Frías |
| 19249631 | Lucas Veríssimo |
| 19232616 | Zé Ivaldo |
| 19215476 | Luan Peres |
| 2000206870 | Gustavo Henrique |
| 19152912 | Mayke |
| 19258929 | Igor Vinicius |
| 19073567 | Willian Arão |
| 2000379979 | Vinícius Lira |
| 14172026 | Gonzalo Escobar |
| 2000256316 | Caio Araújo |
| 78091915 | Christian Oliva |
| 19171250 | Zé Rafael |
| 19102937 | João Schmidt |
| 86000589 | Tomás Rincón |
| 14201730 | Álvaro Barreal |
| 2000206863 | Gabriel Bontempo |
| 2000205667 | Enzo Boer |
| 14183203 | Benjamín Rollheiser |
| 2000088460 | Miguel Terceros |
| 2000417769 | Robinho Junior |
| 19246772 | Thaciano |
| 19249790 | Rony |
| 19024412 | Neymar |

Oliva may show a pill in FM; still **white** = owned at club.

### owned_out_on_loan (pink/red)

| UniqueID | Name |
|----------|------|
| 2000202623 | Luisão |
| 79031724 | Alexis Duarte |
| 2000218555 | JP Chermont |
| 19377228 | Nathan Santos |
| 2000207206 | Kevyson |
| 19368081 | Sandry |
| 19194171 | Patrick |
| 79033967 | Gustavo Caballero |
| 29188479 | Billal Brahimi |
| 19383039 | Moisés |
| 19090895 | Tiquinho Soares |

### inbound_loan (blue)

| UniqueID | Name |
|----------|------|
| 19333767 | Gabriel Menino |
| 14221703 | Lautaro Díaz |
| 30035404 | Gabriel Barbosa |

### +488 clue (do not ship as Senior)

FMT today lists **26** names, all inside this 42. Missing from +488: the 6 whites Falcão, Diogenes, Alex Nascimento, Gustavo Henrique, Caio Araújo, Enzo Boer, plus 10 of 11 outbound (Moisés is in +488). All 3 inbound are in +488.

## Notes

- Identity: `scripts/extract-managed-team.py`. Current list: `scripts/extract-squad-lists.py` (`native-clubid-plus488-v1`)
- SCOPE extract model is club → employed → loaned-out vs at-club. **Inbound (blue) is the gap** — at club, not owned. Lock it; do not expand SCOPE.md
- Next: **T116** (blocked) — same statuses on Bodø/Glimt; gold UniqueIDs already in that ticket. Do not claim T116 this run.

## Blockers

- Club `.dat` intern list is FM Senior **32**, not the gold **42**. Ten owned-out UniqueIDs (Luisão, Duarte, JP Chermont, Nathan, Kevyson, Sandry, Patrick, Caballero, Brahimi, Tiquinho) are person doubles in the save but not referenced from the Santos `.dat` object.
- Moisés (19383039) is **in** that 32-list and gold **owned_out_on_loan** — the 32 vs 31 residual. No loan-object / contract discriminator split inbound vs owned-at vs Moisés.
- Need a second structural path (contract / loan object on the club, not a world walk) before three-status can match gold. Do not claim T116 until that exists.

## Progress

- Tried: person doubles for all 42 UniqueIDs (`02 40` + intern + uid||uid); club UniqueID 335 `.dat` (`tad.`) object; packed intern list; 7f02 job lists; +488; T086 `64ff` loan motif; contract `01 00 6c 07` triplet (too noisy / unbounded).
- Locked: identity club 335 → `.dat` at tadAbs 97919946 → u32 count **32** at 97922104 → person internals → UniqueIDs. Membership = 28 owned_at_club + 3 inbound + Moisés. Dump `tmp/identity/t115-santos-three-status.txt`. Gold in `tests/fixtures/t115-santos-gold.json`. Script `scripts/lock-santos-three-status.py`. Unittest synthetic + skip-unless `data/saves/gameDate8.fm`. No UI. No +488 Senior. No extract-*.py gold IDs.
- Failed: path from club to the other 10 owned-out ids; three-status classifier matching gold.
- Next: HQ / T116 wait — find owned-out list or loan/contract flag on the club object (not person-world scan).
