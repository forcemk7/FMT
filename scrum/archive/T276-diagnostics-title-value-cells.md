---
id: T276
title: Diagnostics — title + value-status cells; kill warning soup
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-09-10
started_at: 2026-09-10
completed_at: 2026-09-10
depends_on: []
---

# T276 — Diagnostics — title + value-status cells; kill warning soup

## Why

Settings Diagnostics dumps Status/Data warnings as a joined soup. When affiliate clubs flake on the same save, the owner cannot jump to one cell and read the concrete outcome. Diagnostics must work as an **index**: each load step is a cell whose status **is** the value (or the miss).

## Scope

- In: Each Diagnostics cell = **title** + **status**; status is the actual value, or the concrete absence (`none`, `unresolved · …`, `dropped · …`)
- In: Promote affiliation / roster-load outcomes that today only live in warning soup into first-class cells (walk count, loan filter, partner resolve, affiliate clubs loaded, skipped identity slots, field coverage known/unknown)
- In: Remove bottom Status warnings / Data warnings soup cells from Settings → Diagnostics
- Out: Live progressive fill during Load (still T215); new RE; renaming every existing cell for polish; Loop D

## Acceptance criteria

- [x] Settings Diagnostics has no joined Status/Data warnings soup
- [x] Affiliation / affiliate-load stages appear as separate title+status cells with concrete values or miss reasons
- [x] Existing connection/load cells remain title+value (or Unavailable/None) — no indirect ok/fail-only labels for those stages
- [x] One commit `T276: …`

## Notes / pointers

- UI: `desktop/src/components/settings-screen.tsx`
- Connector warnings today: `desktop/src-tauri/src/connector.rs` (affiliation report, skipped slots, field coverage)
- Slice of deferred T215 doctrine; does not unfreeze full T215 live-fill

## Progress

Shipped: `status.diagnosticCells` from connector (title + value/miss); affiliation walk outcomes (`loaded` / `dropped · loan-off` / `unresolved · club table` / excluded types) as index cells; Settings renders those cells in load-order section; Status/Data warnings soup removed. `cargo check` clean. Commit SHA in archive after commit.
