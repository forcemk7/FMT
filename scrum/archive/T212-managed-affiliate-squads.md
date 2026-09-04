---
id: T212
title: Load managed affiliate squads (II / NPL)
status: done
priority: 1
owner: cursor-agent
claimed_at: "2026-09-04T09:27:00+02:00"
started_at: "2026-09-04T09:27:00+02:00"
completed_at: "2026-09-04T09:55:00+02:00"
depends_on: [T198, T201, T203]
---

# T212 — Load managed affiliate squads (II / NPL)

## Why

Same-club Club.Teams now mirrors FM for Liverpool / Leicester / Bodø / Legia / Santos / Melbourne Youth. Remaining Loop A gap: **entire managed squads that are separate club entities** — Schalke 04 II (~21), Melbourne Victory (NPL) (~29). Goal = **1:1 mirror of in-game managed players** in FMT (with HA). Empty extra tabs and label wording are out of scope.

## Scope

- In: Discover affiliate clubs that appear on the managed club’s **Squad** tab (not every feeder)
- In: For each such club, load Club.Teams → First (or sole) roster via existing player pipeline; surface as Squad unit(s)
- In: Live verify Schalke II (FM24Continue) and Melbourne NPL against FM totals / atClub / loanedIn / loanedOut (ignore FM tmpgeneratedplayers)
- Out: Empty Youth(0) cleanup; Under 21s vs U21 labels; wiring every Affiliated Clubs feeder; full-world Team table (Loop D)

## Acceptance criteria

- [x] Schalke: FMT shows II with FM-matching real-player counts (First + U19 unchanged)
- [x] Melbourne: FMT shows NPL with FM-matching real-player counts (First + Youth unchanged)
- [x] Club total unique managed players moves toward FM total (Schalke 79, Melbourne 55) excluding temp gens
- [x] Feeders that are **not** on FM Squad tab stay out
- [x] One commit `T212: …`

## Notes / pointers

- T198: affiliate graph probe; II is separate club
- T203: `@0x8E8` flag A/B — NPL/II often **not** on that vector; discovery uses parent-edge + satellite markers
- Labels: affiliate TeamType 0 surfaces as second “First Team” — later ticket

## Progress

- Discovery: parent-edge affiliates not inline on managed blob + satellite name markers (II / NPL / ` 2`) + roster 12..=55. FMLE Main+Permanent+PMF = product meaning; not `0x8E8` byte lock.
- Production: `discover_bteam_affiliate_clubs` → `load_bteam_affiliate_rosters` → Club.Teams → roster; `affiliate_reserve_club_uids` for loan honesty.
- **Melbourne PASS:** FMT total 55 = First 21 + Youth 15 + NPL ~19 (tmp gens out).
- **Schalke PASS:** FMT total 79 = First 37 + U19 21 (FM 26−tmp) + II 21. Empty Youth(0) OK.
- Residual: affiliate tab label still “First Team” (TeamType 0).
- Commit: `dd5ea45`
