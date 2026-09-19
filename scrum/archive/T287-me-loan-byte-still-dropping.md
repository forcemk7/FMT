---
id: T287
title: ME loan-agreement byte still drops clubs (Legia)
status: done
priority: 1
owner: worker
claimed_at: 2026-09-20T00:00:00+02:00
started_at: 2026-09-20T00:00:00+02:00
completed_at: 2026-09-20T00:00:00+02:00
depends_on: []
---

# T287 — ME loan-agreement byte still drops clubs (Legia)

## Why

Match Experience affiliate loan-agreement detection has been "fixed" twice (T245 locked the byte as boolean 0/1; T286 found the live on-value bumped 1→2 and moved to `!= 0`) but Legia Warszawa still drops out while Kaiserslautern and Sparta Praha resolve. Either the wrong byte is still being tracked, or there's a per-club variant the `!= 0` model doesn't cover. The feature already shipped (STATUS "Recently done" T286) and is user-facing — a recurring silent drop erodes trust in it.

## Scope

- In: Re-verify the loan-agreement byte against Legia specifically (and the clubs that already work) — confirm whether it's the same field misread, or a distinct flag / second condition
- In: Falsifiable A/B across known-good (Kaiserslautern, Sparta Praha) and known-bad (Legia) clubs before calling it fixed
- In: Update `research/recipes.md` with whatever is locked or ruled out
- Out: Rebuilding ME card ordering (T253, separately deferred); new affiliate types beyond loan agreement

## Acceptance criteria

- [x] Legia (and the previously-passing clubs) all resolve correctly for the same save — live-verified: Legia now loads alongside Kaiserslautern/Sparta on the Schalke save
- [x] `research/recipes.md` updated with the confirmed byte/condition and what was ruled out
- [x] One commit `T287: …`

## Notes / pointers

- Prior work: T245 (lock byte, on=1), T286 (nested+0x65 != 0, live on=2)
- Check whether Legia's loan agreement is structured differently in-save (e.g. a different affiliation subtype) rather than assuming the byte itself is wrong

## Progress

**Live diagnostic confirms this is a real bug, not stale evidence.** Owner has active players on loan to Legia right now (in-game, confirmed the agreement is active), yet Settings > Diagnostics groups Legia with Melbourne Victory and Daegu FC — the original known-*off* control clubs — under "Dropped loan-off feeders." Internally consistent with itself, but wrong against ground truth.

**Diagnostic dump added** (not yet a fix): `affiliate_links.rs` now carries the raw `nested+0x65` byte (`loanByte`) through `rosterOutcomes` for both dropped and loaded feeder entries, and `connector.rs` appends it to the Settings status text — e.g. "Legia Warszawa [byte=0x00]" — so the actual byte value is visible without reading `fm.exe` directly. `cargo build`/`cargo test --lib fm26::affiliate_links::` — clean, 9/9 passing.

**Byte + type comparison done.** Legia's wrapper type is `0x03` — identical to Kaiserslautern's and Sparta's (the working clubs). "Unlabeled affiliation types: 0x03" is just a missing PGE label *string*, unrelated to the bug. Rules out "different relationship type" as the cause.

**Owner's hypothesis, now the live lead:** Legia's affiliation with Schalke may have started *without* a loan agreement, with the agreement added later in-game. If FM keeps the old and new link side by side in `club+0x118` rather than mutating one record in place, and our raw walk hits the old (no-agreement) one first, `seen_uids` dedup would silently discard the correct, current one — every time, regardless of `!= 0` vs `== 1` vs any other threshold on the loan byte, because we'd never even be looking at the right record.

**Made that checkable without more RE:** the dedup previously discarded a same-UID duplicate silently, invisible even in diagnostics. Now pushes a `"skipped · duplicate uid"` roster outcome (with its own type + loan byte) instead, surfaced as a new Settings cell **"Duplicate affiliation links (uid seen twice)"**. `cargo build` + `cargo test --lib fm26::affiliate_links::` — clean, 9/9 passing. `npx eslint` on `settings-screen.tsx` — clean.

**Duplicate theory dead — no duplicates found.** Legia has exactly one raw link. Confirmed via `cargo run -p fmt --features fm-probe --bin probe-loan-flag` (already-existing, previously-unwired probe binary — read-only, attaches to live `fm.exe`, dumps the full nested blob per affiliate and runs `find_stable_u8_separators`).

**Real finding: `stableU8Separators` came back empty.** No byte in the full 128-byte nested record has one shared value across Legia/Kaiserslautern/Sparta ("on") and a different shared value across Daegu/Melbourne ("off") — because Kaiserslautern and Sparta don't even agree with *each other*: at the `+0x65` window, Kaiserslautern reads `...309a7697...` and Sparta reads `...901fe987...` — different non-zero values, both plausible little-endian pointers. Legia, Daegu, and Melbourne are all-zero across that same window. So the field isn't "one on-value vs one off-value" — it looks like **presence of a pointer/sub-record vs. its absence**, which `find_stable_u8_separators` (exact-value matching) is structurally blind to.

**Added `find_stable_nonzero_separators`** (`affiliation_types.rs`) — a new probe helper alongside the existing exact-value and bit-level ones, checking "all on-blobs non-zero, all off-blobs exactly zero" as its own criterion. Wired into `probe_players_go_on_loan_dump` alongside the pre-existing (but never-wired-in) `find_stable_bit_separators`, plus the full per-club nested-blob hex (previous dump only showed a ±8-byte window around the old `+0x65` lock — too narrow if the real signal sits elsewhere). New unit test added modeling the exact Legia/Kaiserslautern/Sparta pattern seen live. `cargo build`/`cargo test --lib --features fm-probe` and `--no-default-features` — both clean, all passing (7/7 affiliation_types, 53/53 full default suite).

**Both new checks came back explainable, not real signal.** Decoded by hand: the `stableNonzeroSeparators` hits (`0x0E`, `0x12`) are the high byte of the already-known partner-UID field (`+0x0C`, duplicated `+0x10`) — Kaiserslautern/Sparta/Legia all have UIDs under 65536 so that byte is zero for all three; Daegu (5,705,626) and Melbourne (1,300,489) don't, so it's non-zero for them. Coincidence of which clubs were sampled, unrelated to loan status. The `stableBitSeparators` hits (~12 of them) sit inside the repeated heap-pointer regions visible in every dump — with only 3 "on" vs 2 "off" samples, a few spurious bit matches inside pointer bytes is expected by chance, not trustworthy. `stableU8Separators` stayed empty. **Conclusion: the nested 128-byte record does not contain the flag** — documented in `research/recipes.md`.

**Owner's framing: FMLE reads this cleanly as a bool for every affiliate club, so it exists somewhere** — just not where we've been looking. Next candidate: the **wrapper** object, one hop up from the nested record (`AFFILIATION_WRAPPER_PROBE_BYTES` — 128 bytes, already captured per-link as `wrapper_bytes`, never run through any separator search before now).

**Wired in:** `probe_players_go_on_loan_dump` now runs all three separator kinds (`stableU8Separators`, `stableBitSeparators`, `stableNonzeroSeparators`) against **both** regions — nested and wrapper — via a shared `all_separators()` helper, output as `nestedSeparators`/`wrapperSeparators`. Every link row also now carries the full `wrapperHex` dump (previously only `nestedHex`). `cargo build`/`cargo test` clean with `--features fm-probe` and `--no-default-features` alike (53/53 default suite, 7/7 affiliation_types with fm-probe).

**Found it — `wrapper+0x2E`.** `stableU8Separators` on the wrapper region returned 4 candidates; decoded all of them across all 7 links (not just the 5-club on/off sample) using the actual FMLE-labeled ground truth the owner provided (Kaiserslautern/Legia/Sparta = FMLE "Players Go On Loan: True"; Daegu/Melbourne/Schalke II = False/absent). `wrapper+0x2E` is 7/7 correct: `0xFE` for exactly the three True clubs, `0x6C` for everyone else — including Schalke II and Sevilla, which share neither Legia's affiliation type nor its loan status, ruling out a type-byte confound. The other three candidates (`+0xB`, `+0x73`, and the bit-level hits) were ruled out by hand — each broke on at least one "other"-category club (Schalke II or Sevilla landing on the wrong side), consistent with them being heap-pointer artifacts.

**Shipped to production** (not just the probe): `wrapper_players_go_on_loan()` (`affiliation_types.rs`) replaces `nested_players_go_on_loan()` as the actual gate in `affiliate_links.rs`'s feeder-loading loop. Keep rule is `!= 0x6C` (anchored on the off-value, per the T245→T286 lesson — the on-value `0xFE` is a single-save sample and could drift the same way `1→2` did; re-diff via `probe-loan-flag` if a future session disagrees, don't re-harden `==0xFE`). Old nested-byte code kept as historical record, no longer called. Settings diagnostics ("Players Go On Loan filter", "Dropped loan-off feeders", "Affiliate clubs loaded") now read from the wrapper byte automatically — same cells, correct source. New unit test locks in the exact FMLE-cross-validated values. `cargo build`/`cargo test` clean on both `--no-default-features` (54/54) and `--features fm-probe` (8/8 affiliation_types).

`research/recipes.md` updated with the full trail: why `+0x65` failed (never a real separator, `!=0` only worked by accident), the false leads ruled out, and the locked `wrapper+0x2E` finding with its FMLE cross-validation.

**Live-verified on the Schalke save.** Settings diagnostics confirm: Legia now shows correctly alongside Kaiserslautern/Sparta ("Affiliate clubs loaded" all three `[byte=0xFE]`; "Dropped loan-off feeders" correctly down to just Daegu/Melbourne `[byte=0x6C]`), and Match Experience affiliate teams now include Legia Warszawa / Legia Warszawa II rows that weren't there before.

**Bonus find while re-checking on Barcelona (different save): `wrapper+0x2E` does not generalize to affiliationType `0x01`.** Olot (Barcelona's only loan-eligible `0x01` affiliate) has a confirmed-live loan agreement (FMLE + in-game text both say so) but still reads off — `wrapper+0x2E`/`+0x2D` both zero/off-pattern, and `0xFE` doesn't appear anywhere in its full 128-byte nested or wrapper blob, ruling out a simple offset shift. Two uncontrolled variables (`0x01` vs `0x03`, and FM26-native vs FM24→26-converted save) with no second `0x01` sample on hand to isolate either — **not chased further here, deliberately.** Owner agreed: T287's actual scope (Legia/`0x03`) is met; Olot/`0x01` needs real new data before it's actionable, so it's a fresh ticket (T294), not scope creep on this one. Documented in `research/recipes.md`.

**Closing T287 here.** Final verification: `cargo build`/`cargo test` clean on `--no-default-features` (54/54) and `--features fm-probe` (8/8 affiliation_types), plus the live Schalke rebuild check above.
