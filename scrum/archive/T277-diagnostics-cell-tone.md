---
id: T277
title: Diagnostics cell tone — green / yellow / red
status: done
priority: 2
owner: cursor-worker
claimed_at: 2026-09-10
started_at: 2026-09-10
completed_at: 2026-09-10
depends_on: [T276]
---

# T277 — Diagnostics cell tone — green / yellow / red

## Why

T276 made Diagnostics an index of title+value cells. Scanning still costs a read of every status string. A per-cell tone (green / yellow / red) makes failures glanceable.

## Scope

- In: Each `diagnosticCell` carries `tone`: `green` | `yellow` | `red`
- In: Connector sets tone when building cells (green = resolved value; yellow = partial / expected drop / Unknown; red = unresolved / read miss)
- In: Settings Diagnostics shows a small color cue per cell
- Out: Live progressive fill (T215); rewriting status strings; new RE

## Acceptance criteria

- [x] Every diagnostic cell has a tone
- [x] Affiliate miss paths use red (unresolved) or yellow (loan-off / excluded) appropriately; loaded use green
- [x] Settings shows the tone cue without replacing the status text
- [x] One commit `T277: …`

## Progress

Shipped: `tone` on `DiagnosticCell`; connector assigns green/yellow/red; Settings shows a 7px cue on each cell title. `cargo check` clean. Commit: `0e1f397`.
