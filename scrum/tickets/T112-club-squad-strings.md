---
id: T112
title: After club id — find “squad” strings linked to that club
status: ready
priority: 1
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T109]
---

# T112 — After club id — find “squad” strings linked to that club

## Why (plain English)

We know the save’s **club id**. Next brick: find text containing **squad** (or related UI labels) that belongs to **that** club — not random other clubs.

No player list yet. Human-readable dump only.

## Owner UI smoke (hints only — may be custom skin)

Continue Schalke (club **920**). UI showed (counts are smoke, not law):

| UI path / page | Label-ish | Count |
|----------------|-----------|-------|
| Squad > First Team | Schalke 04 **Senior**: Squad Players | 31 |
| Squad > Under 19s | Schalke 04 **U19**: U19 Squad Players | 23 |
| Squad > Schalke 04 II | Schalke 04 II: **Senior Squad** Players | 33 |

Breadcrumbs also say “First Team” / “News” — **may be skin, not native FM strings in the save.**

## What we might find in the binary (hypotheses)

1. **Page titles** — fragments like `Squad Players`, `U19 Squad`, `Senior Squad`, `Senior`
2. **Team display names** — `Schalke 04 II`, `Under 19s`, `First Team` (or only short club name + separate squad type)
3. **No English at all** for squad type — only ids + later resolved UI strings (then string hunt alone is not enough)

## Parallel search plan (first useful hits win)

| Lane | Needles (case-insensitive) | Primary file |
|------|----------------------------|--------------|
| A | `Squad Players`, `U19 Squad`, `Senior Squad`, `Senior:` | `dynamics-c.fm` (Schalke continue) |
| B | `First Team`, `Under 19`, `Schalke 04 II` | same |
| C | any `squad` within a clear link of club UniqueID **920** (document the link rule) | same + compare one native (`gameDate1.fm` / 676) |

Deliverable: `tmp/identity/t112-*.txt` dumps + plain English STATUS (hit counts + example strings).

## Scope / Blind / Acceptance

- In: dumps for ≥1 continue Schalke + ≥1 native; plain English Progress
- Out: player ids; filling Squad UI; claiming Senior lock; T108/T110 revival
- Blind: no `*.fm` / `tmp/` in git; no live `games/*.fm`
- [ ] Dumps exist; owner can read strings without Python
- [ ] One commit `T112: …`

## Progress

**HQ race (2026-08-17) — all three lanes finished:**

- **Lane A** (UI titles: Squad Players / U19 Squad / Senior Squad / Senior:): **0 hits** in early decompress of dynamics-c + gameDate1. Your page titles look **skin/UI**, not save text.
- **Lane B** (full decompress dynamics-c): **hits** — `Schalke 04 II` (11), `Schalke 04` (37), `First Team` (77), `Under 19` (80). II / club names look real; First Team / Under 19 mostly world/UI noise. Proximity-to-920 check used wrong LE bytes in places — treat “near club id” as unverified.
- **Lane C** (`squad` in 64KB *after* identity club id): **0** on Schalke and Liverpool. Squad labels are **not** sitting right after the identity club id.

**Conclusion for next brick:** Do not hunt “Squad Players” / “Senior:” as save law. Prefer **team display names** already in the blob (`Schalke 04 II`, catalog club names) and structural links from club id — not the 64KB-after-identity window.