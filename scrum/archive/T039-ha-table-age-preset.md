---
id: T039
title: HA table Age column + one-click mentor/mentee age preset
status: done
priority: 2
owner: worker
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: [T033]
---

# T039 — Click kid = find mentor; click senior = find mentee

## Why

**Loop:** one-click suitability on the club HA table. T033 writes HA floors only, so a 19yo click still lists other 19yos as “not worse.” FM mentoring is age-gated (mentee **< 24**, **3-year** gap). Age is already on the extract (`dateOfBirth` + `gameDate`); the table just does not show or filter it.

## Scope

- In: **Age** column on the club HA table (DOB → age at save `gameDate`; missing = `—`). Sortable. Same glance job as Unit.
- In: Age is an editable numeric filter key (not 1–20 HA dropdown — allow real ages).
- In: **Every data column is a filter key.** Checkbox / group # are not columns. One ordered list drives both the table (L→R) and the filter key dropdown (top→bottom): Name, Unit, Age, Personality, Media, DET…CON, HAS. No orphan keys, no Age dumped at the bottom.
- In: One-click with **exactly 1** selected player who has a known age **also** writes an Age row into the normal filters (same language as T033; user can edit/drop it):
  - **Find mentor** (clicked age **< 24**): Age **≥ clicked+3**, plus existing T033 HA floors (growth **≥**, CON **≤**)
  - **Find mentee** (clicked age **≥ 24**): Age **≤ clicked−3**, and **invert** HA vs T033 (growth **≤** clicked, CON **≥** clicked) — otherwise kids fail the senior’s ≥ floors and the age ceiling is a trap
- In: Missing age → no Age filter (do not invent). Column `—`. HA preset still runs.
- Out: Two-player age direction (pair stays T033 HA-only). Suggest / seating / auto-pick. CA/PA. New click modes, extra buttons, or a second filter language. Extract / RE. T038.
- Out: Filter on the unit-check column. Global search box. Ranker page. New ops (contains / range). Group-shape meta presets.

## Acceptance criteria

- [x] Table shows Age per row from this save’s DOB + game date; blank DOB is `—` not `0`
- [x] Click a player age 19: filters include Age ≥ 22 and T033 HA ≥ from that row; same-age peers without the gap disappear; selected row stays visible
- [x] Click a player age 27: filters include Age ≤ 24 and inverted HA (e.g. DET ≤ 27yo’s DET); a 30yo with higher Pro is hidden; a 21yo who is not better on that vector can remain
- [x] After one-click, user can delete or loosen only the Age row without resetting HA filters
- [x] Age filter values are not capped at 20
- [x] Filter key dropdown lists every data column in table order (Name → Unit → Age → Personality → Media → DET…CON → HAS); Name / Unit / Age are usable like the rest
- [x] No Suggest changes

## Notes / pointers

- Numbers already in `src/inference/mentoring.ts`: `YOUNG_AGE = 24`, `AGE_GAP = 3`. Copy those two into `web/squad-ha-table.ts` (or export constants). Do not invent a third pair. Do not import Suggest.
- **Heuristic, not engine:** `<24` / `+3` are starting floors (user request + leftover Suggest constants). They are editable after one-click. Do not claim SI locked them.
  - Tutoring-era (FM13–17): tutee **under 23**, tutor **≥23** (captain exception). No 3-year gap found.
  - Mentoring-era (FM19+): [emufm](https://emufm.wordpress.com/2019/03/28/mentoring-on-fm19/) — age is a **weight** with appearances, hierarchy, social group; **no specific age limit**. Same squad required.
  - FMInside: personality change “mainly effective younger than 23.” SEO blogs (18–20 golden / fixed after 21) are not tests.
  - 1 mentor + 2 mentees: common **practice** ([FM-Arena](https://fm-arena.com/thread/13314-ideal-mentoring-setup/) “ideal numerical setup”; EBFM 1+10 ≈ no effect; Passion4FM min 3, often 1 influencer + 2 kids). Not a hard engine ratio. Large mixed groups with ~1:1 still reported to move HA. SoT = Dynamics Estimated influence / effect + actual attribute shifts.
- Age helper: `rosterPlayerAge` / `ageFromDateOfBirth` in `web/roster-data.ts` / `shared/save/types.ts`. `buildSquadHaRow` already computes age for combo match and discards it.
- Preset: `squadHaNotWorsePreset` — extend or sibling for the age + invert branch; keep filters as ordinary `SquadHaFilter` rows.
- Filter UI today uses 1–20 `<select>` (`renderSquadHaFilters` in `web/main.ts`). Age needs a number input or 15–45 options. Today’s key list is Personality, Media, attrs, HAS — missing Name / Unit; Age must not append last.
- One list in `web/squad-ha-table.ts` (e.g. `SQUAD_HA_FILTER_KEYS`) shared by table headers and the key dropdown. Unit values: FT / II / U19. Name/Personality/Media: existing text ops. Kid click stays **find mentor**; second mentee = delete/loosen Age.
- Tests: `tests/squad-ha-table.test.ts`

## Progress

Shipped Age column on the club HA table (DOB + save `gameDate`; missing = `—`) and one-click age direction as ordinary filter rows. `SQUAD_HA_FILTER_KEYS` drives table L→R and the filter-key dropdown (Name → Unit → Age → Personality → Media → DET…CON → HAS). Click exactly one player with known age: **< 24** writes Age ≥ age+3 plus T033 HA ≥; **≥ 24** writes Age ≤ age−3 plus inverted HA (growth ≤, CON ≥). Pair and missing age stay HA-only. Age uses a number input (not capped at 20). Name / Unit are filter keys. Suggest untouched. Copied `YOUNG_AGE = 24` / `AGE_GAP = 3` into `web/squad-ha-table.ts`.

Verified: `npx vitest run tests/squad-ha-table.test.ts` (29 passed); `npx tsc --noEmit`.
