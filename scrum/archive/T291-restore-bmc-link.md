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

## Follow-up (2026-09-22) — link didn't actually open in the packaged app

Owner caught it live: the BMC button did nothing when clicked inside `npm run desktop:stable`/`desktop:dev`, despite T291's original QA passing. Root cause: T291 was verified via `npm run dev` (plain Next.js in a browser tab) — a context where `<a target="_blank">` always works — but was never clicked inside the actual Tauri-packaged window. Tauri's webview doesn't reliably hand off `target="_blank"` navigations to the OS default browser without an explicit mechanism to do so, so the link silently did nothing in the real app.

Considered adding `tauri-plugin-shell`, but building it hit a persistent `crates.io` fetch failure ("schannel: server closed abruptly") — a TLS-layer issue on the dev machine's network path, not something to route around by touching the VPN. Went with a smaller fix instead, requiring no new dependency:

- `desktop/src-tauri/src/commands.rs` — new `open_external(url)` Tauri command, https-only guarded, shells out via `explorer.exe` (not `cmd /C start`, to avoid any shell-metacharacter injection surface since `cmd` reinterprets the joined command line).
- `desktop/src-tauri/src/lib.rs` — registered the command.
- `desktop/src/components/shell-header.tsx` — BMC `<a>` replaced with a `<button>` that calls `invoke("open_external", ...)`, guarded by the same `"__TAURI_INTERNALS__" in window` check already used elsewhere in the codebase for Tauri-only calls.
- `desktop/src/app/fmt-desk.css` — dropped the now-dead `a.shell-bmc` selectors (button is already covered by the existing `button:not(.shell-load)` rule).

Verified: `cargo check --offline` clean (confirms zero new crate/network dependency), `tsc`/`eslint`/`vitest` (142/142) clean, button renders and doesn't throw in the browser dev preview (guarded no-op there, as expected outside Tauri). Owner live-verified the click actually opens the browser in the real packaged app.
