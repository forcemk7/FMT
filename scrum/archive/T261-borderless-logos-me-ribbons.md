---
id: T261
title: Borderless club logos + ME card ribbon chrome
status: done
priority: 2
owner: auto
claimed_at: "2026-09-07T01:19:00+02:00"
started_at: "2026-09-07T01:19:00+02:00"
completed_at: "2026-09-07T01:22:00+02:00"
depends_on: [T260]
---

# T261 — Borderless club logos + ME card ribbon chrome

## Why

Club logos keep getting framed every place we add them — default must be bare. Best players/talent extras should read `{logo}{teamType}`. ME current/best chrome is too neon and misplaces labels.

## Scope

- In: `.club-logo` default = no border / no fill frame (nation-flag can stay framed)
- In: Best players / Best talent extras = `{clubLogo} {teamType}`
- In: ME profile cards — thin even border highlight; Current/Best as top-edge ribbon on the border; cards stay vertically aligned
- Out: Division RE; logo pack RE

## Acceptance

- [x] ClubLogo default has no container border/highlighter
- [x] Ability peeks show logo + teamType
- [x] ME current/best: thin even border + embedded top label; aligned cards
- [x] Commit `T261: …`

## Progress

- `.club-logo` bare by default; nation-flag keeps frame
- Ability peeks: `dashClubTeamChrome` → logo + teamType
- ME: thin even border; Current/Best ribbon on top edge; grid padding for alignment
- Verified: squad-ability-rank tests
- Commit: (pending)
