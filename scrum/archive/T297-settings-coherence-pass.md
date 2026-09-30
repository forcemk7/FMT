---
id: T297
title: Settings coherence pass — section-by-section truth audit
status: done
priority: 1
owner: hq-chat
claimed_at: 2026-09-29
started_at: 2026-09-29
completed_at: 2026-09-30
depends_on: [T215, T290, T292, T293]
---

# T297 — Settings coherence pass

## Why

Final FMT 1.28 ticket. Settings grew across T215/T276–T286/T290/T292/T293 and now carries cells that say what FMT does *not* do, and the same fact stated twice in different words. 1.28 is a trust pass; a Settings page that contradicts or repeats itself undercuts that. Goal: every cell states something true about what the app actually does, once.

## Scope

- In: Walk Settings **one section at a time**, top to bottom, with the owner. For each section:
  1. List what's there (every cell/label/copy line, as rendered).
  2. Check each against what the code actually does — say what's true, what's stale/false.
  3. Propose: keep / reword / merge / remove. Owner decides.
  4. Apply only the agreed edits for that section, then move to the next.
- In: Remove "we do NOT do X" style cells; collapse duplicate facts phrased differently; fix copy that no longer matches behavior.
- Out: New preferences, new diagnostics, new sections, layout/theme changes (T139/T293 territory), backend/RE changes. If a cell is false because the *feature* is broken, note it and spin off — don't fix the feature here.
- Out: T290 telemetry disclosure *meaning* — wording can be tightened, but it must still disclose what's sent and that there's no opt-out.

## Acceptance criteria

- [ ] Every Settings section reviewed with the owner, one at a time, with an explicit keep/reword/merge/remove decision per cell (recorded in Progress)
- [ ] No cell describes something FMT doesn't do; no fact appears twice
- [ ] `tsc`/`eslint`/`vitest` clean on touched files; dev-preview render checked
- [ ] One commit `T297: …` on `FMT/`, **then push** (this ticket says to push)

## Notes / pointers

- Investigate-before-coding applies: present each section's findings and proposed edits, wait for go-ahead, then edit.
- Settings screen: `desktop/src/components/settings-screen.tsx`; preferences store `desktop/src/domain/preferences.ts`; Telemetry section from T290.
- Section order today (T215 + T292 follow-up): User Preferences panel, then Graphics → FM26 → Save → Manager → Club → Affiliations → Teams → Players, plus Telemetry (T290).
- Ordering vs the consolidated 1.28 live test pass: owner's call. Doing T297 first means the pass also covers the cleaned Settings copy.

## Progress

Ground rule set by owner (section 2): **cells hold actual states the app holds, not explainers.** No explainer cells, no hardcoded-green "status" on fixed copy. Owner prefers terse copy.

1. **User Preferences** — keep as-is (owner: most to-the-point section).
2. **Telemetry → renamed "Diagnostics"** (owner: fixer connotation, not data-piping). Dropped the three explainer cells ("What's sent", "Not collected", "Why"). Now three real-state cells: **Anonymous id**, **Last data sent** (the exact payload of the last post, minus anon_id), **Last sent** (timestamp; red + HTTP status on failure). `telemetry.ts` now records the last send result (module store + `useLastSent` hook); load_attempt/load_outcome posted sequentially so "last" is deterministic. Header meta is now real state: "Always on" when Supabase env + Tauri present, else "Not configured" (was hardcoded "Always on"). Supabase table/event names unchanged.
3. **Graphics** — folder cell tone now uses backend `graphicsExists` (was always green because the path string is always set). Dropped "Pack count" (dup of header + rows). Pack cells: title = kind, value = pack name (path was folder + name, a dup of the folder cell).
4. **FM26** (28 → 13 cells). Removed non-state: Can write memory (hardcoded false), Read-only access flags (constant), Mapping schema (hardcoded v2), Memory safety (rewording of Memory access). Removed duplicates of Connection state / Failure stage: Parser status, Pointer validation, Active save, Memory probe, Last successful read, Data source, Product version, Connector message. Last sync now a formatted time (was raw unix ms). Manager registry / Active manager pointers → Manager section, labelled as pointers. FMT version → Diagnostics.
- **Grid holes** (owner-spotted): wide cells mid-list stranded the half cell before them; odd counts left a trailing hole. `packCells` in `SettingsGroup` now puts wide cells last and stretches an odd last half cell.
5. **Save** — removed Season (computed `year/year+1` from the date, not read from FM; wrong Jan–Jun and for calendar-year leagues; used nowhere else). Save = In-game date only. Owner asked for the savegame name: FMT doesn't read it (no save-level object locked; same gap as T190's Save ID). Not added here — spin-off candidate: read loaded save name/path from `fm.exe` memory. No pointers belong in Save (`save_pointer` is actually the human manager object).
6. **Manager** — keep name + registry/active-manager pointers. Manager pick shows "Single human manager" instead of "none" (it only lists candidates on multi-human saves). Name fallback moved to Players (it's about squad player names, not the manager).
7. **Club** — keep as-is.
8. **Affiliations** (backend + frontend). Header was always yellow because list cells went yellow whenever non-empty, even for correct filtering. Excluded / Dropped loan-off now green (intended filtering). "Affiliations club+0x118" + "Unlabeled affiliation types" merged → **Affiliation links** (`N links · 0x03 unlabeled`; yellow only while a type lacks a PGE label). Loan filter → `Active · wrapper+0x2E`. Header count = distinct affiliate clubs from `clubTeams` (was comma-split of a status string). ME teams cell moved to frontend: club name + team type (non-First), so two teams of one club no longer read as duplicates; backend cell + its `club_teams` param removed.

**Final pass (owner rule, 2026-09-29/30):** every Settings cell is either an **action** (User Preferences toggles — untouched) or a **status** cell = one real value + a tone (green working / yellow partial / red error). A normal working load must be all green. Owner asked the rest be done without per-section review.

- Backend `build_load_diagnostic_cells` rewritten: counts only for Skipped squad slots / Name fallback; Manager pick → **Human managers** (count, green); Affiliation links = count, always green when the scan ran (the `0x03` "unlabeled" note removed — `affiliationTypeDisplayLabel` has no callers, so it affects nothing visible); Loan filter = `wrapper+0x2E` / "not needed" when no links; affiliate lists are names only (type/byte suffixes dropped); Duplicates yellow, Unresolved red, everything else green. Removed hardcoded cells: Squad field coverage, Unvalidated fields, Club.Teams discovered, Club.Teams + affiliate players loaded, Squad-tab affiliate clubs (+ unused `club_squad_promoted` counter).
9. **Teams** — removed Load scope (hardcoded `managed-squad`), Clubs loaded (always 1), the two promoted-player cells. One cell per team: `N players`.
10. **Players** — removed Squad/Visible/Fully-scouted players loaded (all = Players loaded), Partial scout reports (hardcoded 0), Mapping coverage (always empty), Squad field coverage / Unvalidated fields (hardcoded). Now: Players loaded, Club employees, Squad collection pointer (from Teams), Skipped squad slots, Name fallback.
- FM26: Process → Process ID (one value); SHA-256 "Not needed" green when the version already matched an entity map; Entity map red "No match for this build" when missing. Graphics "Packs: none" green (optional). Diagnostics "Last sent" = time only (red on failure); section now has a tone.
- **Larger interface tooltip offset** (owner-spotted): root `zoom` was applied twice to the floating positioner. Positioner gets `zoom:1/1.125`, popup `zoom:1.125` (`globals.css`, `data-slot="tooltip-positioner"` in `ui/tooltip.tsx`). Not verified in Tauri — check the Load tooltip with Larger interface on.

Verified: `tsc`/`eslint` clean on touched files (one pre-existing set-state-in-effect lint error in `graphics-packs-panel.tsx`, unchanged line), `vitest` 142/142, `cargo check` clean, `cargo test --lib` 54/54, dev-preview render of every section with no console errors (no save attached — live-save greens go into the consolidated 1.28 pass).

Residuals: read loaded save name from `fm.exe` memory (owner wanted it in Save; no save-level object locked — ties to T190's Save ID). Header button still says "Settings & diagnostics" while a section is now named Diagnostics.
