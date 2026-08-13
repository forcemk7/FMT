# Roadmap

Poverty rule: only the next loop-breaking phase is funded. Later phases are notes, not commitments.

## Phase 0 — Loop exists (shipped — stop expanding)

- [x] HAS ranker / checker / compare
- [x] Career Save → FT / II / U19 + HAS (discovery can still miss units on some saves — do not fund until loans are honest)
- [x] Mentoring (attr-only influence proxy)
- [x] Attributes evolution (CA + HA history)
- [x] Mercenary / regen-only personality match (NEWGEN) — user-verified

## Phase 1 — Mentoring must be creatable, then Dynamics

### 1a — Squad / loan / name honesty (**shipped**)

T004–T009. Closed against user-provided GT — **generalization unproven**.

### 1a.5 — Career Save ingest (**shipped**)

T010 — upload / disk sync commits fresh extract.

### 1a.6 — Blind extract trust + U19 loan ghosts

| Ticket | Focus | Status |
|--------|--------|--------|
| T011 | Incomplete extract cannot look done | **shipped** |
| T012 | U19 at-club excludes outgoing loans; Loans U19 | **shipped** |

### 1a.7 — Personality combo honesty (**shipped**)

| Ticket | Focus | Status |
|--------|--------|--------|
| T013 | Do not label Born Leader without known Det/Lea=20 | **shipped** |

### 1a.8 — Det/Lea extract for recent signings (**funded**)

Gilson-class: HA pack present, **no CA history** (recent signing). Det/Lea must not depend on Progress Report tip.

| Ticket | Focus | Status |
|--------|--------|--------|
| **T014** | Lock + extract Det/Lea without CA history; no decoy poison | **ready #1** |

### 1b — Dynamics lock (**paused** until T014)

1. Ground truth fixtures
2. Binary layout lock → `dynamics-layout-locked.json`
3. Wire `dynamics{}` in extract
4. Mentoring seating consumes Dynamics

## Explicitly unfunded (refuse / defer)

- Sync status pill cosmetics
- Loan crest polish
- “Fix every Millwood-class motif” as open-ended RE
- Upload / decompress / extract **speed rewrite** — T010 already commits fresh extracts; slowness is not the error source (T011: loan unclassified)
- More GT-chasing tickets without a blind failure surface

## Later (unfunded until Phase 1 closes)

- Dynamics labels no longer manual
- Fixture regression polish — only if usage shows breakage

## Discard pile

Quarantined forever unless the loop itself dies without them: see SCOPE.md "Not need-to-have".
