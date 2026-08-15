# FMT — Football Manager 26 companion

Read-only **personality HA** from a Career Save. You make mentoring groups in FM; this is the borrowed look-up so you do not seat a worse senior. Not an editor. Not Genie Scout. Not a mentoring oracle.

## Product wedge

```
Squad (HA, at-club)   Loans (honesty / youth out)   Mentoring   Progress (CA + HA)
```

**Loop:** Squad → Loans → Progress → store unit → create the group in FM.

**Not in scope:** Suggest, editor, full-save GS extract, exe, Stripe, FM27.

## Status

Living backlog, roadmap, and agent handoff: **[`scrum/`](./scrum/)** (start at `scrum/README.md`).

| Area | State |
|------|--------|
| HAS ranker / checker / compare | Not the ship — strip from chrome (T075) |
| Squad HA table (was Personalities) | **Ship** — T073 rename |
| Loans tab | **Ship** — honesty + youth out (T074 cancelled) |
| Mentoring | **Ship** — no Suggest (T071) |
| Progress (CA + HA points) | **Ship** — who to mentor / influence |

## Layout

```
data/raw/          spreadsheet CSV source for catalog
data/fixtures/     binary layout locks + Dynamics ground truth
data/saves/        Career .fm copies FMT extracts (copied from SI games/; never extract the live file)
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
