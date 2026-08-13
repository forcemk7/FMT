# FMT — Football Manager 26 companion

Out-of-game tool for **personality intelligence** from Career Saves: who has the best hidden attributes, how to mentor safely, and whether mentoring actually moved the needle.

## Product wedge

```
Best Personalities (web funnel)     Squad Analyzer (the product)
├── Rank personality × media        ├── Personalities — batch HAS from save
├── Hidden Attributes Calculator    ├── Mentoring — influence-safe groups
└── Compare                         └── Attributes — HA/CA feedback after mentoring
```

**Livelihood loop:** load a save → rank squad personalities → build mentoring groups that won't ruin Determination → watch HA/personality shifts.

**Not in scope (quarantined):** penalty taker ranks, favoured-club scouting zoo, match-HA completeness for its own sake.

## Status

Living backlog, roadmap, and agent handoff: **[`scrum/`](./scrum/)** (start at `scrum/README.md`).

| Area | State |
|------|--------|
| HAS ranker / checker / compare | Shipped (static Pages OK) |
| Career Save → First Team / II / U19 + HAS | Working in `npm run dev` (FT = managed club) |
| Loans tab (club-wide loaned-out) | Shipped — unit grids are at-club only |
| Mentoring suggestions (influence-safe) | Working; loaned-out excluded; Dynamics labels still **manual** |
| Dynamics extract (hierarchy / social / captaincy) | **Active priority** — ground truth fixtures + A/B saves in progress |
| Attributes evolution (CA + personality HA history) | Working; closes mentoring feedback loop |

## Dynamics lock path

1. Ground truth: `data/fixtures/dynamics-ground-truth-*-wip.json`
2. Binary hunt near FT `listAbs` / team body → `dynamics-layout-locked.json`
3. Wire `dynamics{}` in `scripts/extract-first-team-fast.py`
4. Feed Mentoring seating (replace attr-only influence proxy)

Best RE signal: paired saves where **one** player changes hierarchy tier (`dynamics-a.fm` / `dynamics-b.fm` today are a squad move — prefer a pure demotion pair when available).

## Layout

```
data/raw/          spreadsheet CSV source for catalog
data/fixtures/     binary layout locks + Dynamics ground truth
data/saves/        local Career Saves for extract / RE
src/domain/        attributes, ranges, HAS scoring
src/data/          personality / media / case tables
src/inference/     estimate, rank, mentoring, match-combo
shared/save/       extract wrappers + types
scripts/           Python extractors + RE spikes
web/               Vite UI (ranker + Squad Analyzer)
```

## Usage (library)

```ts
import { loadCatalog, estimatePlayer } from "@fmt/ha-core";

const catalog = loadCatalog();
const result = estimatePlayer(catalog, {
  personality: "Spirited",
  mediaHandling: "MF, Unf",
  determination: 15,
  isRegen: true,
});

console.log(result.attributes.pressure);
```

## Scripts

- `npm run dev` — UI + local Career Save APIs
- `npm test` — vitest
- `npm run build` — emit `dist/`
- `npm run build:web` — static Pages build (ranker/checker only)
- `npm run typecheck`
