# Scope

FMT is an out-of-game **Football Manager 26 companion** for personality intelligence from Career Saves.

## Livelihood loop (the only product)

```
load a save → rank squad personalities → build mentoring groups that won't ruin Determination → watch HA/personality shifts
```

Everything else is noise until this loop is reliable and used.

## Product wedge (need-to-have surface)

```
Best Personalities (web funnel)     Squad Analyzer (the product)
├── Rank personality × media        ├── Personalities — batch HAS from save
├── Hidden Attributes Calculator    ├── Mentoring — influence-safe groups
└── Compare                         └── Attributes — HA/CA feedback after mentoring
```

## Need-to-have (do)

- Career Save extract for First Team / II / U19 + HAS — only as required for the loop
- **Reliable Career Save load/refresh into the active store** (upload / overwrite / disk sync) — without this, extract fixes cannot be tested and Mentoring runs on ghosts
- **Blind extract trust:** incomplete name / attrs / loan classification must be visible; Mentoring must not treat partial rows as finished (stop GT-spoon-fed false greens)
- **Mentoring roster honesty:**
  - All at-club club employees extracted **with names**
  - All club outgoing loans extracted and classified (`loanedOut`); Mentoring never seats them
  - Roster / Mentoring pool = **club employees only** (no non-employed bodies)
- Mentoring suggestions that are influence-safe
- Dynamics extract (hierarchy / social / captaincy) **because** mentoring is still on an attr-only proxy — only after roster honesty **and** solid ingest
- Attribute evolution as mentoring feedback
- Static funnel (ranker / checker / compare) only while it still feeds acquisition into the loop
- Binary layout locks / fixtures that unblock the above

## Not need-to-have (discard by default)

- Penalty taker ranks
- Favoured-club scouting zoo
- Match-HA completeness for its own sake
- Wishlist features justified only by "I want…" with no loop breakage
- Sync status **pill chrome** as aesthetics (Up to date / click-to-sync styling) when ingest already works
- Polish, refactors, or adjacent RE that does not unblock mentoring Dynamics or the feedback loop

## Gate (Scrum Master)

Before any ticket becomes `ready`:

1. Which step of the livelihood loop does this fix or unblock?
2. What user behavior (not verbal want) shows this is broken or missing?
3. What is the smallest change that restores the loop?
4. If we never ship it, does the user still get value from steady use of what exists?

If (1)–(3) are weak → **refuse**. Strict refusal while usage is steady is success.
