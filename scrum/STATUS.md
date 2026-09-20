# Status

Last updated: 2026-09-20 (T215 done — Settings restructured; T295/T296 spun off)

## Now

**FMT 1.28 in progress, one ticket at a time.** Owner works strictly sequential — full QA and close-out before the next ticket starts. No parallel ticket work in this phase.

**T215 done.** Owner-verified live on two saves: Schalke (FM24→26-converted) shows correct in-game date/season and correct ages across FT/U19/B/affiliate; Barcelona (FM26-native) shows in-game date/season `Unavailable` and all squad ages missing as a direct consequence. Confirms the age/date architecture itself is sound — Barcelona's native-save date read is a separate, real bug, spun off as **T296**. A repo git-hygiene issue found while closing T215 (large pre-existing uncommitted work unrelated to any ticket) spun off as **T295**, marked priority per owner request.

**Next up: T295** (git hygiene + workflow guardrail) — owner asked for this to jump the queue given its blast radius on every future ticket's commit safety. Suggested sequence: T295 → T296 → T293 → T292 → T290 → T274 → T139 (T296 not urgent-blocking since it's a known, scoped-out limitation, but cheap to slot in early since it's the direct continuation of the original "ages show `--`" complaint).

**T294 blocked, not startable yet** — needs a second affiliationType `0x01` sample (or a native-FM26 `0x03` sample) to isolate a variable T287 couldn't. Flag it when a save surfaces one; don't force it without new data. **Check jointly with T296** — both trace to the same Barcelona native-save confound; may share a root cause.

`research/club-team-display.md` is now the standing reference for club/team display logic — check it before touching any UI surface that names a club or team.

**Residuals (not tickets):** Main/Permanent/PMF affiliation bytes; PGE label for AffiliationType `0x03`; further globals CSS carcass; club page polish; First XI median later. Club shortName RE parked (T235).

## Board — FMT 1.28

| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| T295 | Repo git hygiene cleanup + workflow guardrail | ready | 1 | owner-prioritized; found while closing T215 |
| T296 | In-game date/Season unavailable on FM26-native saves | ready | 2 | spun off T215; likely shares root cause with T294 |
| T290 | Minimal functional telemetry — install → launch → load → outcome | ready | 2 | depends_on T215 (done) |
| T292 | PA masking toggle | ready | 2 | depends_on T215 (done) |
| T274 | Live connect — auto-refresh + honest load button/status UI | ready | 2 | reframed: current "live" is manual snapshot only |
| T293 | Responsive desk layout + UI density preference + min viewport | ready | 2 | depends_on T215 (done); split out of T139 |
| T139 | FMT shell theme (MW90 CTRL 26-inspired) | ready | 3 | visual identity only now — layout/density moved to T293; sequence after it |

## Deferred / not in FMT 1.28

| ID | Title | Notes |
|----|-------|-------|
| T190 | Development all-time CA (save-copy strip) | blocked on Save ID RAM lock; not speculative but expensive — community-fundable later version |
| T210 | Squad card / list density toggle | not need-to-have while usage holds |
| T253 | ME card order by competition / division difficulty | needs RE spike; cosmetic — distinct from T287's correctness bug |
| T275 | World player lookup (Loop D) | existing clubTeam/affiliate/loan data (via T288) stays searchable; full Loop D world-table RE still parked |
| T162 | Player trophy cabinet | blocked: no trophy object lock, and trophy graphics package would conflict with the logos megapack |
| T294 | Loan flag doesn't generalize to affiliationType `0x01` | blocked on a second `0x01` sample (or native-FM26 `0x03` sample) to isolate type-vs-provenance; real bug (Olot), not speculative; check jointly with T296 |

## Cancelled / superseded

- **T199** Reserves — B-team affiliate rosters — **cancelled**. T288 reuses ME's already-built clubTeam resolution rather than reopening this as a standalone feature.

## Recently done

- **T215** Settings restructured into Graphics → FM26 → Save → Manager → Club → Teams → Affiliations → Players → User Preferences; new Save/Manager sections split out, Scores section dropped (owner's own call — "not that useful"), empty User Preferences shell added for T292. Owner-verified live on two saves: age/date architecture confirmed correct (Schalke: FT/U19/B/affiliate ages all correct); Barcelona's native-save date-unavailable failure spun off as T296, not a T215 defect.
- **T287** ME loan-agreement byte relocated: `wrapper+0x2E` (not nested+0x65) — Legia now resolves correctly alongside Kaiserslautern/Sparta on the Schalke save, cross-validated against FMLE's own checkbox 7/7. Found `wrapper+0x2E` doesn't generalize to affiliationType `0x01` (Olot, Barcelona save) — spun off as T294, blocked on more data.
- **T288** Core clubTeam display model — one gate (`isAffiliateClubTeam`) + two building blocks (`managedTeamTypeLabel`, `clubTeamDisplayName`) replacing 4 independent resolvers; fixed Squad B-team inclusion (0x04 "B Club" locked), Player Profile loan + at-club display, Dashboard ME row, Dashboard Best/Talent cards, Profile ME tab card bold/subtitle swap. Live-verified across 2 saves. `research/club-team-display.md` is the standing reference.
- **T291** Restore Buy Me a Coffee link — `<a href="buymeacoffee.com/mrramirez">` back in shell-header.tsx (regressed since T070)
- **T286** Feeder loan-on keep = nested+0x65 != 0 (T245 on=1 → live on=2)
- **T285** FM26 section: drop Load Active Save (shell Load remains)
- **T284** Settings simple collapse: title + status only (no preview row)
- **T283** Settings preview row visible when collapsed (inside summary)
- **T282** Settings critical peeks = same cell grid visuals (1 row)
- **T281** Settings dense rows: no titles/subtitles; ≤3 critical peeks
- **T280** Settings = diagnostics cells only (Teams/Graphics/Scores as cells)
- **T279** Settings: FM26 / Club / Teams / Players / Affiliations / Graphics / Scores + nested diagnostics
- **T278** Diagnostics tone on every cell + visible cue
- **T277** Diagnostics cell tone — green / yellow / red glance cue
- **T276** Diagnostics title+value cells; kill Status/Data warning soup

## Loop

Loop A funded. Loop B = Dashboard. Loop C: Loans + HoYD + GM live; Tactic/TD out of nav. Loop D parked. **FMT 1.28 is a trust + instrumentation + funnel pass across Loop A/B/C, not a new loop.**
