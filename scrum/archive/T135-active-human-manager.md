---
id: T135
title: Select active human manager when registry has multiple
status: done
priority: 2
owner: cursor-agent
claimed_at: 2026-08-25
started_at: 2026-08-25
completed_at: 2026-08-25
depends_on: [T134]
---

# T135 — Active human manager pick

## Why

Stock GS requires exactly one registry slot (`vector` size == 8). Continue / NewGAN saves with an inactive past manager fail: “could not identify exactly one active human manager.” Owner needs the **active** career manager, not a full multi-human product.

## Acceptance

1. Registry may contain 1–32 human slots (not only size 8).
2. Validate each slot (name + contract + club + plausible squad).
3. When multiple validate, select the **active** one by largest squad size (playable career heuristic); warn with candidates + choice.
4. When none validate, fail with a clear manager_registry error (no silent empty desk).
5. Native single-manager saves still behave like stock.

## Out of scope

- Deleting inactive managers in FM
- Speed / full continue 400k index strategy
- Tactics

## Progress

- Multi-slot resolve kept; pick max `squad_len` among validated humans.
- Warning lists all candidates and the chosen club/manager.
- Unit test documents largest-squad preference.
- Commit: see git log T134/T135.
