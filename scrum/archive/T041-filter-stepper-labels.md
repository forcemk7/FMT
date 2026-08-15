---
id: T041
title: Filter labels spelled out + FM ± and loosen-all
status: done
priority: 2
owner: worker
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T039]
---

# T041 — Filter editor: long names, per-row ±, loosen all

## Why

**Loop:** one-click writes ~10 AND floors; user then loosens to see closest mentor fit. Today the key dropdown repeats table abbreviations (DET, Unit, Media). Nudging means opening each value control. Screenshot: after T039 click, Age ≥ 20 + nine HA rows.

Steal FM’s numbered-filter **− / +** (not FM’s checkbox, reorder, or And switch — we already have AND/OR).

## Scope

- In: Filter **key labels** spell out table abbreviations. Table headers stay short.
  - DET → Determination (and PRO/PRE/AMB/TEM/LEA/LOY/SPO/CON → full names; already in `SQUAD_HA_COL_META.title`)
  - Unit → **Squad**
  - Media → **Media Handling**
  - Name / Age / Personality / HAS unchanged
- In: Each **numeric** filter row (Age, HA attrs, HAS): FM-style **−** and **+** that change that row’s number by 1, clamped (HA/HAS 1–20; Age sane band, not 1–20)
- In: Footer: **Clear** → **Clear All** (same action). Next to it, **−1** / **+1** that nudge **all numeric** filters by operator so one-click floors open together:
  - Loosen (−1): `gte` value−1, `lte` value+1 (CON ≤ and Age ≤ get looser, not stricter)
  - Tighten (+1): opposite
  - Skip text rows (Name / Squad / Personality / Media Handling). Clamp as above
- Out: T040. Suggest. Ranker page. FM checkbox / row reorder. New ops. CA/PA. Renaming table column headers (Unit/Media stay on the grid)

## Acceptance criteria

- [x] Filter key dropdown: Determination not DET; Squad not Unit; Media Handling not Media. Table still shows DET / Unit / Media
- [x] On a DET ≥ 15 row, + → 16, − → 14, without opening a dropdown
- [x] After a kid one-click (growth ≥, CON ≤), footer −1 drops DET…SPO floors by 1 **and** raises CON ceiling by 1; Age ≥ also drops by 1
- [x] Clear All still empties all filters (badge 0, full table)
- [x] No Suggest changes

## Notes / pointers

- Labels: `squadHaFilterKeyLabel` in `web/main.ts` currently returns `SQUAD_HA_COL_META.header` (DET) and "Unit" / "Media"
- Values: Age is already a number input (browser spinner). HA/HAS still 1–20 `<select>` — add −/+ beside the value, don’t invent a second filter language
- Helper belongs in `web/squad-ha-table.ts` (nudge one / nudge all by op). Tests: `tests/squad-ha-table.test.ts`
- Footer: `#squad-filter-clear` in `web/index.html` — title already “Clear all filters”
- Do not steal T040

## Progress

- Shipped: filter dropdown uses Determination / Squad / Media Handling; table headers stay DET / Unit / Media.
- Per-row −/+ on Age, HA, HAS (HA/HAS 1–20; Age 0–50). Footer Clear All + −1 loosen / +1 tighten by op (`gte` −1, `lte` +1; skip text and eq/neq).
- Verified: `npx vitest run tests/squad-ha-table.test.ts` (34 passed); `tsc --noEmit` clean. No Suggest / T040 / Ranker changes.
