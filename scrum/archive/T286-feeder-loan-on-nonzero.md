---
id: T286
title: Feeder loan-on keep = nested+0x65 != 0
status: done
priority: 1
owner: auto
claimed_at: "2026-09-11T01:34:00+02:00"
started_at: "2026-09-11T01:34:00+02:00"
completed_at: "2026-09-11T01:40:00+02:00"
depends_on: []
---

# T286 — Feeder loan-on keep = nested+0x65 != 0

## Why

Match experience drops Legia / Kaiserslautern / Sparta as “loan-off” while II loads. Live probe (2026-09-11): same offset `nested+0x65` still separates, but loan-on is **`2`**, not T245’s hardcoded **`1`**. Production `== 1` fails closed.

## Scope

- In: keep feeders when `+0x65 != 0`; document 1→2 history in `research/recipes.md`; fix unit tests + Diagnostics lock copy
- Out: PGE label for `0x03`; Main/Permanent/PMF RE

## Acceptance criteria

- [x] `nested_players_go_on_loan` is true for any non-zero byte at `+0x65` (0 stays off)
- [x] recipes.md records T245 `on=1`, live 2026-09-11 `on=2`, production keep `!= 0`
- [x] Tests cover 0 / 1 / 2
- [x] Commit `T286: …`

## Progress

- Keep = `!= 0`; constants `ON_T245=1` + `ON_OBSERVED_2026_09_11=2` for history
- recipes + Diagnostics `keep!=0 (seen 1|2)`; `cargo test --lib nested_players_go_on_loan` ok
- Commit: `3e8f3a5`
