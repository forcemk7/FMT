---
id: T259
title: Dashboard Best players / Best talent + horizontal rows
status: done
priority: 2
owner: auto
claimed_at: "2026-09-07T00:56:30+02:00"
started_at: "2026-09-07T00:56:30+02:00"
completed_at: "2026-09-07T01:00:30+02:00"
depends_on: [T258]
---

# T259 — Dashboard Best players / Best talent + horizontal rows

## Why

Loop B peeks should answer “who is best now” and “who has the highest ceiling” without mentor heuristics, and must include loaned-out owned players. Rows should read left→right: face · name · extras · hero metric.

## Scope

### Pool (all dash ability widgets)

- Managed-club players by `clubId` (owned), **including** `loanedOut`.
- Do **not** use `isAtClubEmployee` for Best players / Best talent (that drops loans).

### Widgets + order

1. **Attribute changes** (keep)
2. **Best players** — highest **CA** (no age filter)
3. **Best talent** — highest **PA**, age **≤ 20** (includes First Team / loans; do **not** exclude First Team)
4. **Match experience** (keep)
5. **Top personalities** / **Worst personalities** (keep)

Replace **First-team path** (`Prospects` / mentor+Pro gap / exclude First Team). Drop mentor-room ranking from Dashboard peeks.

### Row chrome (horizontal)

`{face} {name}` … `{additionalDetails} {mainDetail}`

| Widget | additionalDetails | mainDetail |
|--------|-------------------|------------|
| Attribute changes | attr change chips | count of changes |
| Best players | current team, PA | CA |
| Best talent | current team, CA | PA |
| Match experience | from → to (logos/types as now) | `#rank pos` |
| Top / Worst | personality abbr chips | HAS |

Slightly more vertical spacing between peek rows / widgets.

### Nav

- Best players / Best talent / Attribute / Top / Worst → profile **attributes** tab
- ME → **match-experience**
- Full-view Back stays `goBack`

## Out

- Mentoring desk; division-ordered ME; app-wide scroll memory; age ≤21 (use ≤20 unless HQ flips)

## Acceptance

- [x] Widget order + titles as above; First-team path gone from Dashboard
- [x] Best talent = PA desc, age ≤ 20, loans + FT included
- [x] Best players = CA desc, loans included
- [x] Rows match additional/main detail split; spacing improved
- [x] Commit `T259: …`

## Progress

- `squad-ability-rank.ts`: owned pool + `rankBestPlayers` / `rankBestTalent`
- Dashboard order + horizontal row chrome; First-team path removed from peeks
- Verified: vitest `squad-ability-rank.test.ts`
- Commit: `380b3db`
