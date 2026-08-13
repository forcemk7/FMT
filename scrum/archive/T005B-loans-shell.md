---
id: T005B
title: "Loans tab shell: HTML tab + section CSS"
status: done
priority: 1
owner: auto
claimed_at: "2026-08-11T21:39:16+02:00"
started_at: "2026-08-11T21:40:00+02:00"
completed_at: "2026-08-11T21:41:05+02:00"
depends_on: [T006]
---

# T005B — Loans tab shell: HTML tab + section CSS

## Why

Integrator needs a tab target and section chrome before wiring render in `main.ts`. T006 fixed FT club honesty — reopen.

## Scope

- In: `web/index.html` — add **Loans** tab button in `.squad-view-tabs` (order: First Team, Reserves, Under 19s, **Loans**, Mentoring). ids: `squad-view-loans`, `data-squad-view="loans"`.
- In: `web/styles.css` — Loans page sections:
  - section header row (“First Team” / “Reserves” / “Under 19s”)
  - empty section: hide entire section OR show muted empty line (pick one; document in Progress)
  - reuse existing `.squad-loan-crest` for crests; personality cards stay existing card classes
  - panel modifier e.g. `.squad-grid-panel.is-loans` if needed
- Out: `web/main.ts` behavior; data module (T005A); extract

## Acceptance criteria

- [x] Tab visible in markup with stable ids/data attributes
- [x] CSS supports three labeled sections + empty handling
- [x] Progress lists selectors/classes T005 must hook
- [x] **No** `web/main.ts` logic (no mode enum / render yet)

## Claim rule

One agent. HTML + CSS only. Do not fight T005A file set.

## Progress

- 2026-08-11: paused for T006; **reopened ready** after T006 done.
- 2026-08-11: claimed → in_progress → shipped shell (HTML + CSS only; no `main.ts`).

### Empty handling (chosen)

**Hide entire unit section** when that unit has no `loanedOut` players (`hidden` on `.squad-loans-section`). When all three are empty, show `#squad-loans-empty` (“No players out on loan”).

### Selectors / classes for T005

| Hook | Purpose |
|------|---------|
| `#squad-view-loans` / `[data-squad-view="loans"]` | Tab button; set `.is-active` + `aria-selected` |
| `.squad-grid-panel.is-loans` | Panel mode (hides `.squad-grid-wrap`, shows loans pane) |
| `#squad-loans-pane` / `.squad-loans-pane` | Loans view root; toggle `hidden` with mode |
| `#squad-loans-empty` / `.squad-loans-empty` | Club-wide empty state |
| `.squad-loans-section[data-loans-unit="firstTeam\|reserves\|under19s"]` | Unit section; set/clear `hidden` |
| `.squad-loans-section-header` | Section label chrome (already in markup) |
| `[data-loans-grid="firstTeam\|reserves\|under19s"]` | Grid mount; fill with existing `.squad-card-wrap` / personality cards |
| `.squad-loan-crest` | Existing crest class on cards (reuse `bindClubLogo`) |

### Verified

- Tab order in markup: First Team → Reserves → Under 19s → **Loans** → Mentoring
- `web/main.ts` untouched
- Grep confirms ids/classes present in `index.html` + `styles.css`
