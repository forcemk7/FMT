# Status

Last updated: 2026-08-13

## Now

**INCIDENT T023.** Only FT shows; sync OS… failures; likely FT extract with `reserves`/`u19` null **wiped** subunits. T014 still blocked. Dynamics paused.

| Area | State | Need-to-have? |
|------|--------|---------------|
| Multi-unit roster + sync honesty | **MELTED** | **Yes — T023** |
| Det/Lea Gilson | Blocked (T014) | After T023 |
| Dynamics | Paused | After T014 |

## Board

| ID | Title | Status | Owner |
|----|-------|--------|-------|
| T023 | INCIDENT: subunit wipe + OS sync harden | ready | — |
| T014 | Det/Lea for Gilson-class | blocked | auto |
| T022 | Seats fill + hover persist | done | — |
| T001–T003 | Dynamics | paused | — |

## Paste (T023)

```
Read scrum/README.md and scrum/AGENTS.md.
Claim T023.
INCIDENT: stop FT-only extracts from wiping reserves/u19; serialize extracts; clear OS/file-lock sync errors; restore Reserves/U19/Loans/Mentoring after a clean full extract.
When finished: mark done (archive + STATUS) before your final reply.
Stay inside SCOPE.md.
```

## Behavior

- User: only FT; other tabs empty; sync fails “OS” something; feels like work wiped.
- SM: not a git wipe — store/sync. Overlapping extracts in `npm run dev` log; OSError from locked `.fm`; null subunits clear prior data.

## Gate

- **T023 only** until green. Do not invent Gilson Det/Lea.

## Blockers

- T014 unchanged.
- User: if FM has the Career Save open, close it or copy `.fm` aside before re-extract.

## Recently done

- Investigation → T023. T022/T021 Mentoring UX earlier.
