# Dynamics layout spike notes (T001)

Screenshot GT: A = `dynamics-ground-truth-baseline-wip.json`, B = `dynamics-ground-truth-post-captaincy-wip.json`.
Do **not** write full `dynamics-layout-locked.json` until hierarchy has a join.

## Verified on A/B (2026-08-13 screenshots)

FT job lists identical (n=33). Hierarchy + social membership identical for all 23 labeled players.
Only captaincy changed: Tusjak/Paco → Gilson/Radović.

### Captaincy — lockable

Immediately after FT job list (`listAbs + 4*n`):

| offset | type | A | B (screenshots) |
|--------|------|---|-----------------|
| +0 | u32le jobId | 300569 Tusjak (C) | 300395 Gilson (C) |
| +4 | u32le jobId | 106935 Paco (VC) | 534057 Radović (VC) |
| +8 | u32le | 0 | 0 |
| +12 | u32le | 0xffffffff | 0xffffffff |

Repro: `tmp/fm-spike/t001-verify-b.txt`. Person-double ±96 for Gilson/Radović/Tusjak/Paco is **unchanged** A→B — captaincy is not on the person double.

### Social groups — lockable

Four successive `u16le` counted job-id lists after motif `b5 1a e7 07 01 f7 02 00 00` (once per save):

| list | n | membership |
|------|---|------------|
| Core | 14 | Paco … Kramarić |
| Secondary A | 8 | Tusjak … Radović |
| Secondary B | 0 | empty |
| Others | 1 | Gilson |

A @ `205192500`; B @ `205193165`. Sets match GT on both saves.

Fallback join: `u16 n∈[8,40]` whose next `n` u32s ⊆ FT jobs, then 2–3 more counted FT lists.

## Still unlocked — hierarchy

Same on A and B (no demotion signal). Failed hunts: parallel u8/u16, person-double/HA-pack scores, count tuples. Social list order is hierarchy-sorted within group — not enough for TL vs HI.

## T002 wire-up (partial until hierarchy)

1. FT jobs at persistTid `193616` + `7f02`.
2. Captain/VC = first two u32le after `listAbs+4*n`.
3. Social = motif → counted lists → `core` / `secondaryA` / `secondaryB` / `other`.
4. Hierarchy: leave `null` until enum/score join exists.
5. Fill `player.dynamics.{hierarchy,socialGroup,captaincy}`.

## Next

**Brute force only** (see T001 ticket). Opportunistic: Gabor tier flip would add an A/B — not a gate.
