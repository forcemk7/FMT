---
id: T023
title: INCIDENT — restore subunits; stop FT-only extract wiping II/U19; harden sync OS errors
status: ready
priority: 1
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: []
---

# T023 — INCIDENT: only FT shows; sync OSError; subunits wiped

## Why

**Loop break (behavior):** App meltdown — only First Team roster; Reserves / Under 19s / Loans / Mentoring empty or unusable; sync fails with an **OS…** style error. Livelihood loop dead without honest multi-unit extract + Mentoring.

**Investigation (SM 2026-08-13):**
1. Sync “OS…” ≈ Python `OSError` / `PermissionError` (often WinError 32 file lock) bubbled raw into status (`extract-first-team-fast.py` fail wrapper → vite NDJSON → `Background sync failed — …`). Live `.fm` open while FM writes / settle timeout returns unstable file. Dev terminal showed **overlapping decompress/extract** streams.
2. Empty Reserves/U19: extract emits `reserves`/`u19`: **null** when discovery skips; persist **clears** prior subunits (`roster-store` explicit null). FT-ok extract after failed II/U19 **wipes** good subunit data. Loans/Mentoring then look empty (no loanedOut / thin pool) — not CSS hiding tabs.
3. Code wipe of Mentoring feature unlikely — module init DOM crash would kill whole app; past TDZ mitigated.

## Scope

- In: **do not clear** stored `reserves`/`u19` when a new extract returns JSON `null` for those keys (keep previous unless extract explicitly returns empty arrays or a successful subunit payload)
- In: serialize server-side extracts (or refuse concurrent) so one save isn’t decompressed by many workers; fail closed on lock / settle timeout with a clear message (not raw OSError spam)
- In: verify Reserves/U19/Loans/Mentoring panes work after a full successful extract on the user’s current save
- Out: Dynamics RE; Mentoring UX polish (T022 residuals); inventing Gilson Det/Lea

## Acceptance criteria

- [ ] Successful FT extract that fails II/U19 discovery does **not** wipe previously stored reserves/u19
- [ ] Concurrent extract storm cannot stack on the same save (mutex or equivalent)
- [ ] File lock / settle failure shows a clear user-facing message (FM may have the file open / retry)
- [ ] After one clean full extract: FT + Reserves + U19 + Loans + Mentoring panes usable again (smoke)
- [ ] Regression test for “null subunit must not clear previous store entry”

## Notes / pointers

- `web/roster-store.ts` upsert null vs omit (~251–258)
- `web/main.ts` persistExtractResult mapping null → clear (~7672+)
- `scripts/extract-first-team-fast.py` fail() OSError string; vite roster API
- User workaround meanwhile: close FM or copy `.fm` out of games dir; wait for **one** extract to finish; check DevTools `fmt.roster.saves.v3` for `reserves`/`u19`

## Progress

_(worker fills)_
