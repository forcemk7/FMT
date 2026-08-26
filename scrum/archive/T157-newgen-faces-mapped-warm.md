---
id: T157
title: Newgen faces via mapped config warm
status: done
priority: 2
owner: cursor-agent
claimed_at: 2026-08-26T17:25:00Z
started_at: 2026-08-26T17:25:00Z
completed_at: 2026-08-26T17:40:00Z
depends_on: [T152]
---

# T157 — Newgen faces via mapped config warm

## Why

T152 warm only copies Cutout `face_{uid}.png`. Squad movers like Corvin Garbe (not in SIOTSI) are newgens: NGRegens maps `r-{uid}` → ethnicity folder files via `_config.xml`. Those never resolve, so silhouettes stick while Cutout players look fine.

## Scope

- In:
  - Background warm: after O(1) megapack miss, one-pass scan pack `_config.xml` / `config.xml` for requested squad UIDs (incl. `r-` portrait targets); copy hits into face-cache
  - Discover `_config.xml` at pack roots (NGRegens)
  - Longer post-warm UI nudge so 50MB config scan can finish
- Out:
  - Hot-path XML parse on every `player_face_data` (keeps UI unfrozen)
  - Full Cutout config index
  - Theme / Settings chrome

## Acceptance criteria

- [x] With NGRegens installed, Load Active Save warms a squad UID that only exists as `person/r-{uid}/portrait` into face-cache
- [x] Load Active Save does not freeze; mapped scan runs off the UI thread
- [x] Soft miss / `fmt-faces-updated` can show the face after warm without remount
- [x] Unit test covers `r-` portrait parse; `cargo test` graphics faces + `cargo check` pass

## Notes / pointers

- Pack: `graphics/NGRegens_Newgens_Megapack/_config.xml` (~53MB)
- Sample: `to="…/person/r-100679936/portrait"` ← `from="CentralEurope/PP12CentralEurope0853"`
- Existing test helper `parse_person_portrait_record` already strips `r-`

## Progress

Root cause: Garbe-class movers miss Cutout `face_{uid}`; NGRegens needs `_config.xml` `r-{uid}` map. Shipped background UID-targeted scan + longer UI nudges/retries. Verified: `cargo test --lib graphics::faces` 4/4 ok. Commit SHA pending.
