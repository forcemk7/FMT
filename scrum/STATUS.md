# Status

Last updated: 2026-09-18 (T291 done — BMC link restored)

## Now

**FMT 1.28 in progress, one ticket at a time.** Owner works strictly sequential — full QA and close-out before the next ticket starts. No parallel ticket work in this phase.

**Next up: T288** (core clubTeam resolution model) or **T287** (ME loan-agreement byte) — both independent, no dependencies. Suggested remaining sequence: T288 → T287 → T215 → T293 → T292 → T290 → T274 → T139 (T292/T290/T293 all depend_on T215; T139 sequenced after T293 so chrome isn't re-skinned before layout changes).

**Residuals (not tickets):** Main/Permanent/PMF affiliation bytes; PGE label for AffiliationType `0x03`; further globals CSS carcass; club page polish; First XI median later. Club shortName RE parked (T235).

## Board — FMT 1.28

| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| T288 | Core clubTeam resolution model → Squad/Loans/Profile/Dashboard | ready | 1 | fixes Spain B-teams, loan display, dashboard ME label |
| T287 | ME loan-agreement byte still drops Legia | ready | 1 | third attempt after T245, T286 |
| T215 | Settings restructure — sections, per-cell status, restore missing fields | ready | 1 | prerequisite for T290, T292 |
| T290 | Minimal functional telemetry — install → launch → load → outcome | ready | 2 | depends_on T215 |
| T292 | PA masking toggle | ready | 2 | depends_on T215 |
| T274 | Live connect — auto-refresh + honest load button/status UI | ready | 2 | reframed: current "live" is manual snapshot only |
| T293 | Responsive desk layout + UI density preference + min viewport | ready | 2 | depends_on T215; split out of T139 |
| T139 | FMT shell theme (MW90 CTRL 26-inspired) | ready | 3 | visual identity only now — layout/density moved to T293; sequence after it |

## Deferred / not in FMT 1.28

| ID | Title | Notes |
|----|-------|-------|
| T190 | Development all-time CA (save-copy strip) | blocked on Save ID RAM lock; not speculative but expensive — community-fundable later version |
| T210 | Squad card / list density toggle | not need-to-have while usage holds |
| T253 | ME card order by competition / division difficulty | needs RE spike; cosmetic — distinct from T287's correctness bug |
| T275 | World player lookup (Loop D) | existing clubTeam/affiliate/loan data (via T288) stays searchable; full Loop D world-table RE still parked |
| T162 | Player trophy cabinet | blocked: no trophy object lock, and trophy graphics package would conflict with the logos megapack |

## Cancelled / superseded

- **T199** Reserves — B-team affiliate rosters — **cancelled**. T288 reuses ME's already-built clubTeam resolution rather than reopening this as a standalone feature.

## Recently done

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
