---
id: T293
title: Responsive desk layout + UI density preference + minimum viewport
status: done
priority: 2
owner: claude-hq-chat
claimed_at: 2026-09-28
started_at: 2026-09-28
completed_at: 2026-09-29
depends_on: [T215]
---

# T293 — Responsive desk layout + UI density preference + minimum viewport

## Why

FMT's core design principle is "no pagination required" — a desk should show everything without scrolling. In practice today that's only true on the one viewport it was built against. Owner's own fullscreen screenshot (Squad → Player Profile, taller-than-standard laptop display) shows a large dead-space band below the content — the desk is fixed/custom-fit to one machine's window height, not actually responsive. Separately: the owner deliberately runs FMT at a small font/UI size (personal preference — reads as more professional), but that may be a readability barrier for other downloaders. Both are the same underlying problem — the app assumes one viewport and one text size — so they're one ticket.

## Scope

- In: Desks (start with Squad → Player Profile, the one in evidence; extend to Dashboard/Squad list/Loans/HoYD/GM) fill available application window space responsively — verified on at least two different viewport heights/aspect ratios, not just the owner's own display
- In: Decide and lock a **minimum supported application viewport/window size** — below it, defined/graceful behavior is allowed to differ; at or above it, "no pagination" must hold
- In: A UI density / font-scale preference in Settings > User Preferences (small = current default size, larger = more readable) — both settings must still satisfy "no pagination" at the locked minimum viewport
- Out: Any chrome color/typeface changes (T139); new desk content; per-attribute color coding
- Out: True fluid scaling to arbitrary tiny windows — the minimum-viewport decision explicitly bounds the problem instead

## Acceptance criteria

- [x] Player Profile (and Squad) fill available window height/width responsively across at least two tested viewport sizes, no large unused dead space at the owner's own resolution
- [x] Minimum supported viewport is documented (in `research/` or the ticket Progress) and the no-pagination guarantee is demonstrated at exactly that size
- [x] UI density preference exists in Settings > User Preferences; default matches today's small size; larger setting still satisfies no-pagination at the minimum viewport
- [x] One commit `T293: …`

## Notes / pointers

- Evidence: owner screenshot, Squad → Marko Radović profile, fullscreen, taller-than-16:9 laptop display, substantial empty space below the Hidden/Personality/General attribute rows
- Requires T215's User Preferences section to exist before the density toggle can be added
- Sequence before T139 if both are picked up close together — re-skinning colors on a layout about to be restructured is wasted work

## Progress

**Pass 1 (2026-09-28) — uncommitted, awaiting owner build check.** Uncommitted on purpose: owner is building the app to check it before the ticket's single commit. Files: `desktop/src/domain/preferences.ts`, `desktop/src/components/settings-screen.tsx`, `desktop/src/components/fmt-app.tsx`, `desktop/src/app/globals.css` (T293 block at end), plus this ticket + STATUS.

- **Dead-space cause:** `.attribute-desk-panel > .attribute-desk` is pinned at natural height (`flex:0 0 auto`, "do not stretch"), and `.player-dossier`'s `min-height:100%` can't resolve against the auto-height `.screen-slot`, so extra window height landed as a blank band.
- **Fill fix:** on Player Profile the screen slot becomes a definite-height flex column (same pattern as the compact Dashboard) and the dossier is a size container (`overflow:auto` as fallback below the minimum size). Attribute row padding grows with `100cqh` above the ~684px the dossier has at the 1180x740 default window, capped at 9px, so rows stay aligned across columns. Squad, Loans, HoYD and GM not touched yet.
- **Density:** new `largeUi` preference (default off = today's size), "Larger interface" toggle in User Preferences, applied as `html[data-density="large"]{zoom:1.125}`, which behaves like browser zoom in WebView2.
- **Checked:** `tsc` clean outside tests (test-file TS errors pre-exist at HEAD), `vitest` 142/142, and the eslint error at `fmt-app.tsx:397` (set-state-in-effect) also pre-exists at HEAD. Dev preview at 1280x720: toggle flips `data-density`, sets zoom 1.125, canvas stays exactly 720 high, and the setting survives a reload. No real save in dev preview, so the profile fill hasn't been seen.
- **Open:** minimum viewport not locked yet. The Tauri min is 880x720, but some layouts may not fit that at Large. Decide from the owner's check.

**Pass 2 (2026-09-29) — uncommitted, awaiting owner build check.** The owner rejected pass 1's growing row spacing, confirmed the direction (no scrolling; accept empty space on tall displays), and delegated the layout call. Files added in this pass: `desktop/src/domain/window-size.ts` (new), `desktop/src/components/player-profile-screen.tsx`, `desktop/src-tauri/tauri.conf.json`, `desktop/src-tauri/capabilities/default.json`.

- **Locked minimum window: 1180x780 client (logical px).** A 1080p laptop at 125% scaling leaves about 784 once the Win11 taskbar and title bar are gone, and that's the most common downloader setup. Tauri `minWidth`/`minHeight` are now 1180/780 and the default height 740 → 780. Width 1180 was already the real floor: the old `.app-canvas{min-width:1180px}` clipped anything narrower even though Tauri allowed 880.
- **Measured, not estimated:** the dev preview was fed a mocked `__TAURI_INTERNALS__` snapshot (outfield and GK player). Before this pass the outfield profile needed ~1075px of height and at 800 the bottom rows were *clipped* (not scrollable). Budget then: shell 56, header 68, facts 147, tabs 44, desk 712 (row pitch 25.8), padding ~48.
- **Found:** attribute text renders at 14px, not the intended 10px. The `.attribute-desk .attribute-column span{font-size:inherit}` reset (0,2,1) outranks `.attribute-desk .attr-row-label` (0,2,0). Left as is, since 14px is what the owner has been using.
- **Fix, Player Profile only (`.player-dossier`-scoped CSS at the end of globals.css):** tabs moved into the header row (markup: `Tabs` now wraps the whole dossier); photo 68→48, name 29→24px; facts cells 68→46; tighter dossier, band and heading padding; row padding 3.4→0, so pitch 25.8→18.9. Text size unchanged.
- **Result at 1180x780:** outfield ends at 765 (15px spare), GK at 732; no scroll in either. Removed pass 1's growing-spacing CSS.
- **Larger interface vs the minimum:** 1.125x zoom can't fit 1180x780. The minimum window now scales with density (`applyMinWindowSize` → Tauri `setMinSize`, and the window grows if it's currently smaller; permissions `core:window:allow-set-min-size`/`allow-set-size` added). Large minimum is 1328x878: verified outfield ends at 860 and GK at 822, no scroll. Trade-off: Large isn't usable on a 1080p@125% laptop, where Windows scaling already enlarges everything.
- `tsc` clean outside tests, `vitest` 142/142. `eslint` on touched files shows only the pre-existing `fmt-app.tsx` set-state-in-effect error (now line 399).
- **Not yet done:** Squad, Loans, HoYD and GM haven't been checked at 1180x780. The Tauri-only window-size calls are untested in the dev preview (no-op there) and need the owner's build.

**Pass 3 (2026-09-29): pass 2's compression reverted by owner decision.** The owner judged the tighter profile a downgrade and asked for the original layout with a larger minimum window. `player-profile-screen.tsx` restored to HEAD and the profile budget CSS removed. Kept: the density preference and zoom, and `window-size.ts` with the density-scaled minimum.

- **Locked minimum window: 1180x1060 client (logical px).** Measured in the mock-data dev preview with the original layout: rows at their natural 24.9px, the outfield profile ends at 1057 and GK at 1014; at exactly 1180x1060 there's no scroll and nothing clipped. Tauri `height`/`minHeight` are 1060 and `minWidth` is 1180. With Larger interface on, the minimum is 1328x1193.
- Known trade-off, accepted by the owner: displays with less than ~1100 logical px of usable height (e.g. 1080p at 125%) can't show the full minimum window.
- Still open: Squad, Loans, HoYD and GM haven't been checked at the minimum size; the Tauri window-size calls need the owner's build.

**Pass 3 follow-up (2026-09-29):** in the owner's build at 1180x1060 the Attributes tab fits, but the Development tab (chart + desk) overflows by ~31px, estimated from the owner's screenshot scrolled to bottom (the mock preview can't render the chart: history lives in the local DB). Minimum/default raised to **1180x1100**; Larger interface minimum is 1328x1238.

**Closed (2026-09-29), owner: "good enough, close it".** Shipped: minimum/default window of 1180x1100 client (Tauri config plus a runtime `setMinSize` that scales with density); a "Larger interface" preference (default off, 1.125x root zoom, minimum 1328x1238); Player Profile layout unchanged from before T293. Verified: mock-data dev preview measurements (Attributes tab fits at 1060) and the owner's live builds (Attributes fits; the Development overflow of ~31px led to the 1100 bump). Not verified: Development, Match experience and the other desks at exactly 1100, and the Larger-interface window growth in Tauri. These go into the end-of-1.28 consolidated test pass alongside T290 and T139. Deviations from acceptance: the profile doesn't fill tall displays; the owner explicitly accepted empty space below the content instead of stretched spacing. The pre-existing 14px-vs-10px attribute font specificity quirk is left as is (not in scope).

