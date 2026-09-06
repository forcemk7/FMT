# FMT first-party RE recipes

**Role:** Locked offsets and verdicts discovered **in this project** (tickets + live A/B).  
**Companion:** public tools / steal modes → [`ecosystem.md`](./ecosystem.md).  
**Agent law when editing live-read code:** `.cursor/rules/fm-live-read.mdc`.

Update this file when a ticket locks or discards a recipe. Prefer recipes here over resurrecting deleted probe modules.

**Last updated:** 2026-09-05 (T220 — moved to `research/`)

---

## How this R&D layer is meant to work

1. **Product tree stays thin** — production load code only (`affiliate_links`, Club.Teams walk, entity-map fields).
2. **Knowledge compounds here** — so FMT can stay maintainable across patches, support adjacent OSS tooling, and publish learnings without shipping RE scrap heaps.
3. **Do not revive discarded approaches** listed below without new evidence + a ticket.
4. External community research stays in `ecosystem.md`; **this file is FMT ground truth**.

---

## Affiliates / Squad-tab reserves

**Durable edge (T214):**

- Vector at managed `club+0x118` / `+0x120` → wrapper → nested partner UID `@+0x0C` (also seen `@+0x10`).
- Wrapper: `+0x00` = managed club ptr, `+0x08` = nested record, **type at `+0x30`**.

**Type map (locked):**

| Byte | Meaning | Squad tab? |
|------|---------|------------|
| `0x01` | Normal Affiliated Club | no |
| `0x08` | II Club | **yes** |
| `0x10` | Good Relations | no |
| `0x11` | Likely Friendly | no |

**Production:** type walk first (allow-list `0x08`); T212-style satellite merge only for NPL / unmapped types; unmapped `+0x30` → Diagnostics `Map AffiliationType 0xNN`.

**Cancel A/B:** cancelling inbox affiliation shrinks `+0x118` by cancelled count (edge confirmed).

**Schalke FM Affiliates (Squad-class ground truth):** II, Daegu, Kaiserslautern, Legia, Melbourne Victory, Sparta Praha. FMLE-only friendlies (Duisburg, Twente, …) are **not** Squad tabs.

### Open

- Main / Permanent / Players Move Freely **bytes** still unlocked.
- Sub / B / C / 2 / 3 / Feeder / etc. type values unmapped; NPL still needs satellite or a locked type.

### Do not revive

- Treat `club+0x8E8` slots as FMLE affiliation Type/flags — they are **Relationship-like** catalogs (`Permanent` often `0x4F` at `+0xD`), wrong container (Münster / Hannover 96 II noise).
- Byte-diff II heap (`link club@+0x160`) vs `@0x8E8` for Main/Permanent/PMF.
- Port AppCake `Relationship.Permanent@0xD` for club affiliations.
- Expect free FMLE checkbox A/B to write RAM (Save Changes needs license).

**Code today:** `fm26/affiliate_links.rs` + `affiliation_types.rs` (+ `blob_scan` helpers).

---

## Club.Teams / TeamType

- **Club.Teams** MSVC vector: `club+0x18` begin / `club+0x20` end (entity-map 24/32).
- **TeamType:** `team+0x28` (entity-map 40) — First / under19s / reserves; do not classify same-club youth by `" ii"` / name hacks when TeamType works.
- **Team name:** `team+0x18` full; **`team+0x20` shortName** (validated Schalke `Schalke 04 U19`). When short empty or still `FC …`, strip one legal-form prefix for profile (T231).
- **Tab labels (T229):** managed club → TeamType (`First Team`, `Under 19s`, …); affiliate → shortName (`Schalke 04 II`).
- **Profile Club fact:** player’s team shortName via `squadTeamUid` (short form, never TeamType).
- **Team→club:** `+0x30` (48). **Team.Players:** begin/end 56/64.
- Separate-club German II: resolve **affiliate club** first (above), then Club.Teams on that club.

Tickets: T200, T201, T206, T211, T212, T229, T230, T231.

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
| 2026-09-05 | T220: home is `research/`; T219 probe fossils stripped |
| 2026-09-05 | T219: initial first-party recipe book; strip probe fossils |
