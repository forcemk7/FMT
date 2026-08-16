---
id: T103
title: Page shell — header identity + four tabs + one pane
status: done
priority: 1
owner: Auto
claimed_at: 2026-08-16T12:11:00Z
started_at: 2026-08-16T12:12:00Z
completed_at: 2026-08-16T12:30:00Z
depends_on: [T102]
---

# T103 — Page shell — header identity + four tabs + one pane

## Why

Identity upload and save cards are locked (T099–T102). The window still buries club / date / + / saves inside the Squad toolbar, with FMT + coffee alone in `.app-header`. Owner approved the FM club-screen chrome: one page, identity in the header, four tabs, one pane.

## Scope

Lift existing chrome. Do not invent a second app.

```
FMT    {club_name}    {game_date}                    +   saves   coffee
---------------------------------------------------------------
Squad    Loans    Mentoring    Progress
---------------------------------------------------------------
|  existing pane for the selected tab                         |
```

- In: `.app-header` shows **FMT**, active **club name**, **in-game date** (same card format: Mon DD, YYYY or `—`), then **+**, **saves**, **BMC** (T070). No save → `No save`
- In: Tabs sit under the header as page tabs, order **Squad | Loans | Mentoring | Progress**. Same four panes already in `index.html`. Reserves / Under 19s stay hidden (not top tabs)
- In: + / saves keep T101–T102 behavior (overlay menu, update-same-name, tooltip). Move the controls into the header; do not restyle the cards
- In: Empty pane when there is no save (prompt to +). Active save with empty `players[]` still shows the tab chrome
- Out: Extract Python. HA columns / filters. Save-card layout. Native roster (T087). Deleting hidden `#rank` / checker / compare markup. Theme rewrite. Cloud URL (T077)

## Blind (non-negotiable)

- Do **not** git add `data/saves/`, `*.fm`, `tmp/`
- Do **not** put Club ID or FM24/FM26 in the header (cards + tooltip already have them)
- Do **not** resurrect Rank / Checker / Compare as nav
- Do **not** make First Team / Reserves / U19 top tabs

## Acceptance criteria

- [x] Header matches the shape above (vitest chrome on `.app-header` / tabs)
- [x] Club + date come from the Active save; switching saves updates the header
- [x] Four tabs still switch the existing panes; hash restore (`#roster/mentoring` etc.) still works
- [x] + / saves / BMC still work from the header
- [x] One git commit `T103: …` on FMT/

## Notes / pointers

- `web/index.html` `.app-header` (FMT + BMC today). `#roster-save-controller` holds + / saves. `.squad-view-tabs` already has the four labels (Reserves / U19 `hidden`)
- `web/main.ts` `syncRosterSavesMenu` / active save club + `gameDate`
- Owner mock: header identity; tabs; one table. Chrome only

## Progress

Shipped: page shell chrome. `.app-header` is FMT · Active club · in-game date (`formatInGameDateRow`, Mon DD, YYYY or —) · + · saves · BMC. No save → `No save`. Club ID / FM24/FM26 stay on cards + tooltip. Four tabs sit under the header (`page-tabs`); Reserves / U19 stay hidden. Empty pane prompts +; Active save with empty `players[]` still shows tabs. Hash restore uses `hasActiveSave()` so `#roster/mentoring` survives an empty roster. Save-card layout / extract unchanged.

Verified: `npx vitest run` t103 + t075 + t070 + t102 + t101 + t100 + t095 + t088 + squad-route (29 passed). Restart `npm run dev`. No committed `.fm`.
