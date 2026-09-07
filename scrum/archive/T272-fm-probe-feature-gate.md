---
id: T272
title: fm-probe feature-gate + Cursor rule (quiet builds)
status: done
priority: 2
owner: auto
claimed_at: "2026-09-07T03:42:00+02:00"
started_at: "2026-09-07T03:42:00+02:00"
completed_at: "2026-09-07T03:45:00+02:00"
depends_on: []
---

# T272 — fm-probe feature-gate + Cursor rule (quiet builds)

## Why

Default `cargo` / `tauri build` prints ~50 dead_code RE leftovers. Keep them for research; silence product builds; teach agents via Cursor rule.

## Scope

- In: Cargo feature `fm-probe`; default build `allow(dead_code)` unless feature on
- In: `.cursor/rules/fm-probe-gate.mdc` + AGENTS / live-read pointer — new RE helpers use `#[cfg(feature = "fm-probe")]`
- In: `cargo check` quiet; `cargo check --features fm-probe` re-enables dead_code warnings
- Out: Deleting RE helpers; mass module moves

## Acceptance

- [x] Default `cargo check` in src-tauri: 0 warnings
- [x] Feature exists; rule + AGENTS point agents at it
- [x] Commit `T272: …`

## Progress

- Feature `fm-probe`; `lib.rs` cfg_attr allow(dead_code) when off
- Rule `fm-probe-gate.mdc` (alwaysApply); AGENTS + fm-live-read pointers
- Verified: default `cargo check` → 0 warnings; `--features fm-probe` → 51 warnings
- Commit: (pending)
