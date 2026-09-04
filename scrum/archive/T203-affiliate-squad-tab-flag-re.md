---
id: T203
title: RE — affiliate squad-tab flag bytes (FMLE A/B)
status: done
priority: 1
owner: auto
claimed_at: "2026-09-04T04:20:00+02:00"
started_at: "2026-09-04T04:20:00+02:00"
completed_at: "2026-09-04T04:46:00+02:00"
depends_on: [T201]
---

# T203 — RE — affiliate squad-tab flag bytes (FMLE A/B)

## Why

Same-club sides are locked (Club.Teams). Separate-club reserves (German II and equivalents) that appear on the managed club **Squad** tab are affiliates, not Club.Teams children. FMLE exposes editable labels such as Main / Permanent / Players Move Freely — those are **UI names for fields**, not proven memory names. Finding the underlying bytes (via FMLE toggle A/B) lets FMT filter which affiliate clubs feed the Squad tab, then reuse Club.Teams on that club.

## Scope

- In: Probe that dumps managed-club link-vector (`@0x8E8`) heap structs with **u8/u32 grids** around the affiliate club pointer (`@+0x160`) suitable for one-flag FMLE A/B
- In: Offline **diff helper** (two probe JSON / hex dumps → changed offsets)
- In: Progress documents exact human protocol (toggle one LE control, re-probe, pick stable offset that separates squad-tab affiliate vs feeder)
- Out: Wiring production load (empty `affiliate_reserve_club_uids` stays until offsets locked — follow-up ticket)
- Out: Hardcoding Schalke II UID; assuming LE label strings exist in RAM

## Acceptance criteria

- [x] Probe output includes per link-vector slot: struct pointer, club ptr @0x160, `structBytesHex`, u8 + u32 grids ±64 around club-pointer field
- [x] Diff helper (script or unit-tested fn) lists offsets that changed between two dumps
- [x] Progress: human FMLE A/B steps + how to interpret II vs feeder
- [x] Production load unchanged (no unfinished filter)
- [x] One commit `T203: …`

## Notes / pointers

- T198: `relationshipCandidates` / layout lock; II uid 3609393 on Schalke
- `affiliate_links.rs`: `MANAGED_CLUB_BTEAM_LINK_VECTOR_OFFSET` 0x8E8, `AFFILIATE_LINK_STRUCT_CLUB_POINTER_OFFSET` 0x160
- `npm run probe:affiliate-flags` / `fmt-probe affiliate-flags`
- Hypothesis: squad-tab affiliates are a flag combination FMLE edits; confirm by byte flip, not by string search
- FMLE labels are **display names for editable fields only** — lock the bytes they flip, then map which combination marks Squad-tab affiliates

## Progress

### Shipped

- `probe_affiliate_squad_flag_slots` — dumps all 8 `@0x8E8` slots with club `@+0x160`, `structBytesHex`, `u8GridAroundClubPointer` (±64), `u32GridAroundClubPointer`, feeder-catalog hint
- `diff_hex_blobs` / `diff_affiliate_struct_hex` + unit tests; `desktop/scripts/diff-affiliate-flag-dumps.py`
- CLI: `npm run probe:affiliate-flags` → feature `affiliate_flags_probe` / `fmt-probe affiliate-flags`
- Wired `affiliate_links` + `blob_scan` (+ `executable` / `fmt_log` needed for connector identity path)
- Production extract path not given an affiliate filter

### Human FMLE A/B protocol

1. FM save loaded; prefer managed club with a Squad-tab reserve (Schalke II) **and** a feeder that is not on Squad.
2. `npm run probe:affiliate-flags > before.json`
3. In FMLE, open **one** affiliate relationship; toggle **exactly one** editable control (e.g. Main / Permanent / Players Move Freely — UI labels only).
4. `npm run probe:affiliate-flags > after.json`
5. `python desktop/scripts/diff-affiliate-flag-dumps.py before.json after.json`
6. Note `slot` + `offset` that flipped. Repeat per control on II vs a feeder; lock offset(s) that are on for Squad-tab affiliates and off for feeders.
7. Follow-up ticket: filter link slots by those bytes → fill reserve club UIDs → Club.Teams on that club.

### Verified

- `cargo test --lib -- diff_hex_blobs affiliate_struct_hex u8_grid` — 3 passed
- `cargo build --features affiliate_flags_probe --bin fmt-probe` — ok

### Commit

_(SHA after commit)_
