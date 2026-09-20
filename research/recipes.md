# FMT first-party RE recipes

**Role:** Locked offsets and verdicts discovered **in this project** (tickets + live A/B).  
**Companion:** public tools / steal modes → [`ecosystem.md`](./ecosystem.md).  
**Agent law when editing live-read code:** `.cursor/rules/fm-live-read.mdc`.

Update this file when a ticket locks or discards a recipe. Prefer recipes here over resurrecting deleted probe modules.

**Last updated:** 2026-09-20 (T296 — Barcelona date failure was save-freshness, not a native-save offset bug)

---

## How this R&D layer is meant to work

1. **Product tree stays thin** — production load code only (`affiliate_links`, Club.Teams walk, entity-map fields).
2. **Knowledge compounds here** — so FMT can stay maintainable across patches, support adjacent OSS tooling, and publish learnings without shipping RE scrap heaps.
3. **Do not revive discarded approaches** listed below without new evidence + a ticket.
4. External community research stays in `ecosystem.md`; **this file is FMT ground truth**.

---

## Affiliates / Squad-tab reserves

**Durable edge (T214):**

- Vector at managed `club+0x118` / `+0x120` → wrapper → nested record UID `@+0x0C` (also seen `@+0x10`).
- Wrapper: `+0x00` = managed club ptr, `+0x08` = nested record, **type at `+0x30`**.

**Type map (locked / in use):**

| Byte | Meaning | Squad tab? | Roster load? |
|------|---------|------------|--------------|
| `0x01` | Normal Affiliated Club | no | **yes** if nested+0x65 loan-on |
| `0x03` | Feeder partners (Schalke: Legia / Kaiserslautern / …) — **PGE label TBD** | no | **yes** if nested+0x65 loan-on |
| `0x04` | B Club (Barcelona save 2026-09-18: Barcelona B, PGE-confirmed) | **yes** | **yes** |
| `0x08` | II Club | **yes** | **yes** |
| `0x10` | Good Relations | no | no |
| `0x11` | Likely Friendly | no | no |

**Players Go On Loan — LOCKED T287 (2026-09-20): `wrapper+0x2E`, not nested+0x65.** `wrapper_players_go_on_loan()` in `affiliation_types.rs`. Loan-off = `0x6C`. Keep rule = **`!= 0x6C`** (anchor on the off-sentinel, not the on-value — see rationale below).

| When | Evidence | Region / offset | Values |
|------|----------|------------------|--------|
| T245 2026-09-06 | Schalke Legia/Sparta/KL vs Daegu/Melbourne (FMLE nested term) | nested `+0x65` | on=`1`, off=`0` → kept `==1` |
| T286 2026-09-11 | Same Schalke save live probe | nested `+0x65` | on=`2`, off=`0` → kept `!=0` |
| T287 2026-09-20 | Same Schalke save, Legia now has a **live, real, active** loan agreement (players actually loaned there) — reads `0x00` at nested `+0x65`, identical to true-off Daegu/Melbourne. `+0x65` proven wrong. | — | — |
| T287 2026-09-20 | `probe-loan-flag` re-run against **wrapper** region (`AFFILIATION_WRAPPER_PROBE_BYTES`, never scanned before), cross-checked against FMLE's own "Players Go On Loan" checkbox for all 6 named Schalke feeders | wrapper `+0x2E` | on=`0xFE` (Kaiserslautern/Legia/Sparta — FMLE: true), off=`0x6C` (Daegu/Melbourne/Schalke II — FMLE: false/absent) — 7/7 links, including two (Schalke II `0x08`, Sevilla `0x11`) that share Legia's neighborhood but not its `0x03` type, and one (Daegu/Melbourne) that **does** share the `0x03` type but not the flag — rules out both a type-byte and a region confound |

**Why nested `+0x65` failed:** it was never a real signal. `find_stable_u8_separators` on the nested blob came back **empty** — Kaiserslautern and Sparta don't even share a value with each other at `+0x65` (`0x309a7697` vs `0x901fe987`, both pointer-shaped). T286's "keep != 0" only ever worked by accident (off was reliably `0`, on was **whatever non-zero pointer byte happened to land there**). `find_stable_bit_separators` and `find_stable_nonzero_separators` (both added T287) also came back empty/false-positive on the nested blob — the one nonzero "hit" (`+0x0E`/`+0x12`) was the high byte of the already-known partner-UID field (`+0x0C`), a coincidence of which clubs happened to have UIDs over/under 65536, not a loan signal.

Constants: `PLAYERS_GO_ON_LOAN_WRAPPER_OFFSET=0x2E`, `PLAYERS_GO_ON_LOAN_WRAPPER_OFF_T287=0x6C`. Old nested-byte constants/function (`PLAYERS_GO_ON_LOAN_NESTED_OFFSET`, `nested_players_go_on_loan`) kept in source as historical record only — no longer called from production. **Single-save sample for the on-value (`0xFE`)** — mirror the T245→T286 lesson: if a future session shows a different on-value, that's expected and fine (re-diff via `probe-loan-flag`'s `wrapperSeparators`, extend this table); do **not** re-harden to `==0xFE` — the off-value is the stable anchor.

**RE toolkit added T287** (`affiliation_types.rs`): `find_stable_bit_separators` (existed, never wired into `probe-loan-flag` before now) and `find_stable_nonzero_separators` (new — "all on-blobs non-zero, all off-blobs exactly zero," catches presence/absence fields like a null-vs-set sub-record pointer that exact-value matching misses because the non-zero value differs per club). `probe-loan-flag` now dumps and separator-searches **both** the nested and wrapper regions (`nestedSeparators`/`wrapperSeparators` in its JSON output), plus the full 128-byte hex per region per link (previously only a ±8-byte window around the old nested lock).

**Residual, not chased this round:** FMLE also shows `Permanent: True` for Schalke II only (long-term/owned-style link) and `Main: True` for every link in this sample (no variance → unfindable via separator search here). Byte offsets for these still open — see `Main / Permanent / Players Move Freely bytes still unlocked` below.

**Open: `wrapper+0x2E` does not generalize to affiliationType `0x01` (T287, 2026-09-20).** Barcelona save, Olot (`0x01`, "A national partnership in which players are loaned"): FMLE confirms `Players Go On Loan: True`, in-game text confirms it explicitly ("Barcelona will be able to send players on loan to Olot") — but FMT reads it off. Checked: `wrapper+0x2E = 0x6C` (off), `wrapper+0x2D = 0x00` (off-pattern too), and `0xFE` does not appear **anywhere** in Olot's full 128-byte nested or wrapper blob — rules out a simple offset shift; whatever encodes this for `0x01` is a different mechanism, not a relocated version of the same byte. **Two tangled, uncontrolled variables, not yet isolated:** affiliation type (`0x01` vs the `0x03` the lock was built from) and save provenance (this Barcelona save is FM26-native; the Schalke save the `0x03` lock came from is FM24→26-converted). Blocked on data, not effort — Barcelona has exactly one `0x01`-type affiliate and nothing to diff it against. Needs either a second `0x01` sample (on or off) or a native-FM26 save with a `0x03` affiliate to isolate which variable actually matters. Tracked as its own ticket, not bundled into T287's (met, narrower) scope.

**New candidate variable, unchecked (T296, 2026-09-20):** this Olot test ran on the same Barcelona save T296 found sitting at its exact load date with **zero days ever simulated** — and T296 confirmed at least one other field (`player_current_date_offset`) reads as broken purely because of that freshness, not because of native-vs-converted provenance or a real offset bug. The Olot read above was taken before the owner advanced the save; it has since been advanced (`2025-07-14` → `2025-07-15`+). Worth a free re-check (no new RE, just re-read Olot's flag now) before spending effort isolating type-vs-provenance — save-freshness is now a third, previously uncontrolled variable in this A/B.

**Resolved (T296, 2026-09-20): Barcelona's `player_current_date_offset` failure was save-freshness, not a native-save offset/profile bug.** T215 found Barcelona (FM26-native) reading `In-game date: Unavailable` with every squad band's ages missing as a consequence (`squad_game_date` never resolves). Live probe (`probe-game-date`, new — mirrors `probe-loan-flag`) against the attached Barcelona process found:

- `person_birth_date_offset` (136) resolved correctly for 30/31 sampled first-team players — the entity map / profile is fine on native saves, ruling out a broad profile mismatch.
- `player_current_date_offset` (512) was unreadable for all 31 players. A ±96-byte shift scan found one tempting candidate (`+4`, near-identical `2022-08-13/14` across the whole squad) that turned out to be a false positive once cross-checked against the owner's actual in-game date (`2025-07-14`).
- Owner confirmed Barcelona is a **control save that had never been advanced past its load date**. Advancing exactly one day (`2025-07-14` → `2025-07-15`) made Squad ages resolve correctly with **no code change** — proving `player_current_date_offset` is a per-player "last processed" cache that FM only writes once its normal day/match/training tick touches that player. On a save sitting at its exact load moment, nobody in the squad has been touched yet, so the field is genuinely unset — not wrong, not shifted.

**Not** the same root cause as the `0x01` loan-flag gap directly below — that stays open on its own. The native-vs-converted framing in both original write-ups was a **save-freshness confound**: Barcelona (0 days simulated) vs Schalke (played to year 2046) differ enormously in how "cooked" their per-entity caches are, independent of native-vs-converted provenance. Any future field that looks broken specifically on a fresh/lightly-played save should be checked against this before assuming an offset or profile problem: **advance a few in-game days first.**

`probe-game-date` (`desktop/src-tauri/src/bin/probe_game_date.rs`, `connector::probe_game_date_dump()`, `fm-probe`-gated) kept in-tree as a reusable tool — dumps raw windows + a brute-force shift scan around any documented date offset across the whole sampled squad, and flags shifts that decode consistently across every player (strong signal) vs. sporadically (noise/sentinel).

**Production:** type walk first — roster allow-list `0x08` \| (`0x01`/`0x03` + loan-on); then **one hop** from each loan-on feeder `+0x118` for type `0x08` II (ME-only, e.g. Kaiserslautern II). Squad desk filters out `0x01` / `0x03` / `matchExperienceOnly`. T212-style satellite merge only for NPL / unmapped types; other unmapped `+0x30` → Diagnostics `Map AffiliationType 0xNN`. Feeders: Club.Teams **First + Reserves + Under-N/Youth**; direct managed II: First as Squad 2nd side; feeder→II: First only, ME-only.

**Loan honesty (T256):** `loanedOut` suppresses only loans whose destination UID is an **internal reserve** affiliate — Squad-tab `0x08` II (and type-less satellite / NPL). **Do not** put `0x01`/`0x03` feeders or ME-only feeder→II UIDs in that set — U19→Legia/Kaiser etc. must stay outgoing.

**Squad desk clubTeams (T257):** Show only managed First / U19 / II (and satellites) with **loaded players > 0** (or manager First). Hide empty shells (Youth(0)). Feeders (`0x01`/`0x03`) and `matchExperienceOnly` hops stay off Squad — stamped ME-only at load.

**ME loan competition (T260):** Outgoing `loanedOut` players keep parent `squadTeamUid`. Same-pos ranks must still pull them onto the **loan club First Team** via `loanClubId` (not parent roster). Without loan team uid, do **not** place them on loan-club Under N / Reserves cards.

**Schalke evidence (2026-09-06):** `7/12` links mapped labels; `Map AffiliationType 0x03`; only `0x08` II was resolving before `0x03` allow-list. FMLE-only friendlies (Duisburg, Twente, …) stay out (`0x10` / `0x11`).

**Cancel A/B:** cancelling inbox affiliation shrinks `+0x118` by cancelled count (edge confirmed).

### Open

- PGE display name for `0x03` (still `Map AffiliationType 0x03` in UI).
- Main / Permanent / Players Move Freely **bytes** still unlocked.
- Sub / C / 2 / 3 / Feeder / etc. other type values still unmapped (`0x04` B Club locked 2026-09-18); NPL still needs satellite or a locked type.

### Do not revive

- Treat `club+0x8E8` slots as FMLE affiliation Type/flags — they are **Relationship-like** catalogs (`Permanent` often `0x4F` at `+0xD`), wrong container (Münster / Hannover 96 II noise).
- Byte-diff II heap (`link club@+0x160`) vs `@0x8E8` for Main/Permanent/PMF.
- Port AppCake `Relationship.Permanent@0xD` for club affiliations.
- Expect free FMLE checkbox A/B to write RAM (Save Changes needs license).
- Runtime Schalke name-needle auto-diff / candidate lock for Players Go On Loan (replaced by nested+0x65).

**Code today:** `fm26/affiliate_links.rs` + `affiliation_types.rs` (+ `blob_scan` helpers).

---

## Club.Teams / TeamType

- **Club.Teams** MSVC vector: `club+0x18` begin / `club+0x20` end (entity-map 24/32).
- **TeamType:** `team+0x28` (entity-map 40) — First / under19s / reserves; do not classify same-club youth by `" ii"` / name hacks when TeamType works.
- **Team name:** `team+0x18` full (load `clubTeams.name`; FT may fall back to linked club name).
- **`team+0x20` shortName:** optional youth diagnostic only (U19 validated). **Not** the UI display contract (T235) — empty on FT/II in live evidence.
- **Tab labels (T235):** managed → TeamType; affiliate → full team name.
- **Profile Club fact:** full team name via `squadTeamUid` (same `name` field).
- **Team→club:** `+0x30` (48). **Team.Players:** begin/end 56/64.
- Separate-club German II: resolve **affiliate club** first (above), then Club.Teams on that club.

Tickets: T200, T201, T206, T211, T212, T229–T235.

---

## Person origin (regen)

- **`person+0xD5`:** `1` = database, `0` = game-generated; `isRegen = (byte == 0)` (T216).
- **Not law:** UID ≥ 1.9B, face pack `r-{uid}`, FSS `person+0x18` bit `0x08` (youth team, not newgen).

---

## World tables (Loop D direction — parked)

Prefer `game_plugin` object-table walk (People/Club/Team slots) over heap/idiom “player registry”.  
Stable slot offsets and public ports: `ecosystem.md` recipe R1 + `.cursor/rules/fm-live-read.mdc`.

**Discarded for world index:** `player_registry` idiom/heap experiments (removed T219) — do not resurrect as the world strategy.

---

## Field decode

Use FMSuperScout `Fields.cs` + `desktop/src-tauri/entity-maps/index.json`.  
Already matched in map: UID, CA/PA, positions, attrs, names, nation, DOB, contract ptr, personality, TeamType, Club.Teams, origin `@0xD5`.  
Next free wins when ticketed: wage `contract+0x20`, expiry `+0x48`, guide/transfer value, team competition `@0x50`.

---

## Removed probe surface (T219)

Deleted from the product tree (knowledge retained above / in ticket archives):

- Probe modules: `agreement_table`, `club_affiliates`, `duisburg_type_ab`, `editor_affiliations`, `affiliation_type_census`, `pge_affiliation_sign`, `player_origin`, `player_registry`, `fmle_*`, `index_signature`, `club_team_anchors`, `team_names`, unused `roles`/`tactics`, stub `data/`
- `fmt-probe` binary + `affiliate_flags_probe` feature + npm `probe:*`
- Local dump piles (`desktop/*.json` RE scratch, `*.inflated.bin`, stderr companions)

Re-probe when needed: write a **new** minimal probe under a ticket; start from this file + archives — do not restore the scrap heap wholesale.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-09-20 | T296: Barcelona date-unavailable was save-freshness (never-advanced save), not a native-save offset/profile bug; `probe-game-date` added |
| 2026-09-05 | T220: home is `research/`; T219 probe fossils stripped |
| 2026-09-05 | T219: initial first-party recipe book; strip probe fossils |
