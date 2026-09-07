---
id: T253
title: ME card order by competition / division difficulty
status: deferred
priority: 4
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T250]
---

# T253 — ME card order by competition / division difficulty

## Why

Max same-pos CA (T250) is a weak proxy for *match experience level*. A feeder First with high CA in a weaker league can sort ahead of a lower-CA side in a stronger division (e.g. Ekstraklasa vs 2. Bundesliga vs CFL). In-game ladder sense is closer to **which division the team plays in**.

## Scope (when claimed)

- In: Replace (or secondary-sort under) max-CA within TeamType band using a locked **competition / division difficulty** signal from live memory — aligned with FM’s division ranking where possible (Bundesliga → Ekstraklasa → 2. Bundesliga → CFL → U19 leagues, etc.)
- In: Same signal should inform ME **Best** (equal-rung First hops) once locked — T271 ripped equal-rung CA rank intentionally
- In: Shortest RE path to try: **team → division → reputation**
- In: Document the offset/recipe in `research/recipes.md` once locked
- Out: Blind RE spike without a clear field; parent-logo hacks; inventing reputation from name strings

## Claim gate (do not start until)

1. A direct competition/division difficulty value (or a proven better proxy) is identified in RAM / public tooling, **or**
2. HQ explicitly funds a short RE spike with a falsifiable A/B (named clubs + expected order)

Until then keep T250 max-CA sort; Best stays higher-rung-only (T271).

## Acceptance (when claimed)

- [ ] Within First (and other) bands, card order matches agreed division difficulty for a fixture set of teams
- [ ] U19 / youth leagues sort after senior divisions as specified
- [ ] recipes.md updated; commit `T253: …`

## Progress

Deferred — CA proxy ships; division RE not funded now. Intended path: team → division → reputation (also for Best equal-rung).
