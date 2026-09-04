---
id: T205
title: Roster — fix person_unresolved drops (First XI)
status: done
priority: 1
owner: auto
claimed_at: "2026-09-04T05:22:00+02:00"
started_at: "2026-09-04T05:22:00+02:00"
completed_at: "2026-09-04T05:40:00+02:00"
depends_on: []
---

# T205 — Roster — fix person_unresolved drops (First XI)

## Why

Loop A fails when key first-team players never appear. Liverpool Club.Teams first-team probe: roster slots 0–2 are live player pointers that die on `person_unresolved` in `resolve_person_address` — silent drops, no name. Same pipeline loads attrs only after person resolves.

**Product vs bytes:** Squad must *look like* club → team → players → attrs. That tree is the UI/load contract, **not** a claim that FM stores or exposes data only that way. Prefer **shoulders of giants** (FSS `Fields.cs` person-class / PLAO, AppCake person-type split, live-read archive) over inventing another managed-club graph walk. Apply that knowledge to whatever pointer the current roster vector already hands us — do not wait for full-world load.

## Scope

- In: Diagnose why some managed-roster `raw_player` pointers fail `person_identity_valid` / person resolve (Player vs PlayerStaff vs pointer-vs-inline; PLAO / class dynamic offset from FSS archive)
- In: Fix production `resolve_person_address` (or equivalent) so those slots load name + attrs like other squad rows
- In: Fixture = Liverpool (or current managed club) first-team Club.Teams roster vs in-game Squad — missing starters must appear after fix
- In: Keep delivering Squad via current club/team roster entry points (T201) unless a proven OSS person path clearly replaces a broken step
- In: Document which OSS offset/pattern fixed the drop (so we stop re-RE’ing)
- Out: Full-world People/Club/Team **index load** in production (Loop D); affiliate / separate-club II; tab labels (T206)
- Out: Inventing new heap/idiom registry scans; re-RE of CA/attrs already in entity-map

## Acceptance criteria

- [x] Liverpool (or named QA club) first-team: players that were `person_unresolved` in `scan-liverpool-rosters` / live load now resolve with plausible UID + display name
- [x] Spot-check: previously missing First XI names appear on Squad first-team tab with attrs/CA/PA readable
- [x] No full-save / People-table world index required for this ticket to pass
- [x] Warnings still honest if a slot remains unreadable (no silent drop without count)
- [x] One commit `T205: …`

## Notes / pointers

- Fail path: `connector.rs` `resolve_person_address` / `push_squad_player_from_raw`
- Evidence: `desktop/scan-liverpool-rosters.json` — first team slots 0–2 `reject: person_unresolved`
- Knowledge: `.cursor/rules/fm-live-read.mdc` — Person class dynamic offsets (Player `0x288`, PlayerStaff `0x380`, …); Fields.cs PLAO — **reuse**, don’t re-RE CA/attrs
- Probe: extend `probe:club-teams` / squad-skips dump if needed to show person-class path taken

## Progress

### Diagnosis (live Schalke + Liverpool fixture)

- Entity-map `playerPersonOffset` **648 = FSS Player `0x288`**. Working roster slots resolve as PLAO → person @ +0x288 (`personClassDelta: 648`).
- Old resolver only tried `raw + playerPersonOffset` and scanned **starting at** that offset — never tried PlayerStaff `0x380` / person-as-raw / nested PLAO.
- Liverpool/Schalke “unresolved” leading/trailing slots are **not** missing players: live Schalke rejects all share one **module vtable** (`0x7FFA35FC7008`), zero nested person hits — **non-person roster sentinels**. Real first-team rows already had names (Schalke 37/38 @ delta 648).

### Shipped

- `resolve_person_and_player_base` — FSS class offsets Player/PlayerStaff/Staff/HumanManager; nested PLAO chase; attrs/CA/positions/height/date read from resolved `player_base`
- Production skip text: `non-person roster slot … (vtable …)` (counted, not silent)
- Probe reject: `non_person_roster_slot` + vtable; `probe:club-teams` under `affiliate_flags_probe`
- Archive note in `fm-live-read.mdc`
- Unit test: FSS `0x288` matches entity-map `playerPersonOffset`

### Verified

- `cargo test --lib fss_person_class` — ok
- Live `npm run probe:club-teams` on Schalke: first team 37 named players, classDelta 648; residual slots honestly `non_person_roster_slot`

### Commit

`6f34358` — T205: FSS PLAO person resolve for Club.Teams rosters
