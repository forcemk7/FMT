---
id: T291
title: Restore Buy Me a Coffee link (regressed since T070)
status: done
priority: 1
owner: worker
claimed_at: 2026-09-18T00:00:00+02:00
started_at: 2026-09-18T00:00:00+02:00
completed_at: 2026-09-18T00:20:00+02:00
depends_on: []
---

# T291 — Restore Buy Me a Coffee link

## Why

T070 shipped a header BMC link Aug 15 2026. It's gone from the current shell — `desktop/src` has zero occurrences of "coffee" and zero external links anywhere, almost certainly lost in a header/chrome rewrite since (T139/T141/T158/T226/T284 era). Money funnel is a funded goal for FMT 1.28 — cheapest win available; not a paywall, a straightforward test of whether the community will fund development.

## Scope

- In: Re-add a visible link to `https://buymeacoffee.com/mrramirez` in the current header/chrome, `target=_blank rel=noopener`
- In: Same honest copy as T070 (optional thank-you, not required to use the table)
- Out: Stripe / custom funding flow (explicitly deferred — BMC is enough while it's still unknown whether anyone will pay); new placement research beyond "visible without hunting" in the current shell
- Out: Changing anything else in the header/chrome layout

## Acceptance criteria

- [x] Link visible without hunting in the current shell
- [x] Opens BMC in a new tab
- [x] No other header/chrome behavior changed
- [x] One commit `T291: …`

## Notes / pointers

- Prior art: archived `scrum/archive/T070-buy-me-a-coffee.md`
- Verify the current header/chrome component before assuming T070's old component still exists

## Progress

Shipped: `desktop/src/components/shell-header.tsx` — added a real `<a href="https://buymeacoffee.com/mrramirez" target="_blank" rel="noopener noreferrer">` coffee-cup icon link in `.shell-tools`, between the Load Data button and Settings, styled with the existing ghost/icon button variant plus a new `.shell-bmc` CSS hook in `desktop/src/app/fmt-desk.css` so it matches the Settings icon's chrome coloring (`--chrome-fg` / `--chrome-bg` / hover states). Title/aria-label: "Buy me a coffee — optional, not required to use FMT".

Verified: `npm run dev` (plain Next.js, no Tauri) in the Browser pane — link renders visibly in the header with no save loaded, `find` confirmed `href="https://buymeacoffee.com/mrramirez"` on an actual `<a>` (not a JS-only fake button). `npm run lint` — 17 pre-existing errors/19 warnings elsewhere in the codebase (bands.ts, match-combo.ts, match-best.ts, rebrand-fmt.js, and a pre-existing shell-header.tsx effect-setState lint on line 145 that predates this change), zero new issues on the added code. No other header/chrome behavior touched.

Commit: T291: restore Buy Me a Coffee link (see git log).
