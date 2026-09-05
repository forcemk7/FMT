# FM ecosystem index

Living catalog of **public** Football Manager tooling, offsets, and recipes that can unblock FMT.  
Compound here instead of rediscovering via brittle heap walks.

**Maintained:** update this file when you find, verify, or discard a source.  
**Last sweep:** 2026-09-04  
**Operational RE law:** `.cursor/rules/fm-live-read.mdc` (auto on `fm26/**`)  
**FMT product fork:** FMLE-class **read** core → Gameplay Support UI. Not live editing. Not BepInEx in product.

---

## How agents maintain this

1. **Before** inventing offsets / heap / idiom scans for a ticket: search this file first.
2. After any web/GitHub find that is FM-related and public: **add or refresh a row** (date, license, steal mode).
3. If a repo dies, goes private, or proves useless: mark `status: dead` / `discard` with one-line why — do not delete history.
4. Prefer **recipes + offsets** we can reimplement in Rust over copying GPL wholesale (check license).
5. Closed commercial tools stay as **benchmark / A/B only**, not source.

Sweep hints (repeat when stuck on RE):

```
Football Manager 26|FM26 memory|game_plugin|FmOffsets|FMScoutFramework|live editor scout github
FM26 BepInEx plugin Fields.cs CA PA
```

Watch: GitHub topics / new repos mentioning FM26, fmscout.com news, SortItOutSI CE tables, FM-Arena threads.

---

## Steal modes (use these labels)

| Mode | Meaning for FMT |
|------|-----------------|
| `port-pattern` | Reimplement algorithm in Rust (table walk, bounds check) |
| `offsets` | Copy/adapt numeric layouts into `entity-maps/` |
| `architecture` | Object model / load order insight only |
| `benchmark` | Speed / feature bar; no code |
| `a-b-oracle` | Live compare against running tool |
| `discard-product` | Useful knowledge; must not ship that stack (e.g. BepInEx) |
| `dead` | Stale for FM26 or abandoned |

---

## Tier A — plug / port first (open, FM26-relevant)

### JelmerBouma1985/fm-ai-assistent
- **URL:** https://github.com/JelmerBouma1985/fm-ai-assistent  
- **What:** Java RAM reader → H2/MCP; Linux + Windows  
- **Steal:** `port-pattern` — `FmOffsets` object-table walk (`PeopleOffset` 0x150, Club 0xF8, Team 0x180, `slotPtr+0x80` → begin/end). Build→RVA map + **signature score-scan** when RVA stale.  
- **Why:** Closest open implementation of FMLE-class **full-world** load.  
- **License:** check repo  
- **Status:** active · verified 2026-09-04

### mavarobli/FMSuperScout
- **URL:** https://github.com/mavarobli/FMSuperScout  
- **What:** BepInEx IL2CPP plugin dumper + local web scout  
- **Steal:** `offsets` from `plugin/Fields.cs` (CA@0x264, attrs, contract wage/expiry, personality). `discard-product` for BepInEx itself (SCOPE).  
- **Why:** Best open FM26.3 field map; entity-map already matches CA/PA/attrs.  
- **Status:** active · verified 2026-09-04

### TobiasTest22/GlassScout
- **URL:** https://github.com/TobiasTest22/GlassScout  
- **What:** Tauri live process reader (FMT origin — see `NOTICE-GlassScout.md`)  
- **Steal:** `architecture` — process/memory/scanner/entity-map layering; managed-squad path.  
- **Why:** Already in tree; keep for Loop A; **not** the world-index strategy.  
- **Status:** upstream · imported 2026-08-25

### AppCakeLtd/FMScoutFramework
- **URL:** https://github.com/AppCakeLtd/FMScoutFramework  
- **What:** Opened closed framework for FM17–FM22  
- **Steal:** `architecture` — `ObjectManager` MainAddress → typed object arrays; person vtable split; TeamType@0x28.  
- **Why:** Ancestor of commercial FMSE/FMLE mental model.  
- **Status:** stalled at FM22 · still valuable · verified 2026-09-04

---

## Tier B — lineage / older open (recipes still teach)

### ThanosSiopoudis/FMScoutFramework (+ forks Hamish1969, sptndc, niklasnguyen)
- **URL:** https://github.com/ThanosSiopoudis/FMScoutFramework  
- **What:** GPL .NET realtime scout framework FM14–16  
- **Steal:** `architecture` — Realtime vs Cached modes; versioned offset files; GameManager attach.  
- **Status:** dead for FM26 binaries · pattern alive

### robeady/fm-explorer
- **URL:** https://github.com/robeady/fm-explorer  
- **What:** CSV dump / editor consuming **FMScoutFramework.dll** from FMSE  
- **Steal:** `architecture` — documents that commercial editors shipped the framework as a DLL.  
- **Status:** dead for FM26 · historical proof of shared core

### FM Scout Editor (FMSE) archives
- **URL:** https://www.fmscout.com (FMSE free after discontinuation Feb 2024)  
- **What:** Commercial editor FM17–23; shipped `FMScoutFramework.dll`  
- **Steal:** `dead` as dependency; `architecture` if inspecting old DLL for slot naming only.  
- **Status:** discontinued · free licenses for old FM

---

## Tier C — closed benchmarks / oracles (no source expected)

| Tool | URL / path | Steal | Notes |
|------|------------|-------|-------|
| **FM Live Editor 26** | fmscout.com · local `C:\Program Files\FM26 Live Editor\fmle26.exe` | `benchmark` + `a-b-oracle` | Packed ~11.6MB; string HIT `game_plugin`; no cleartext FMScoutFramework. Free scout, paid save. Online after patches. |
| **FM Genie Scout 26** | fmscout.com | `benchmark` | Deep scout UI; closed; Stam hosts, Eugene builds. Pair with FMLE for advanced filters. |
| **FMRTE 26** | https://www.fmrte.com/ | `benchmark` | Closed realtime editor + scout; Win/Mac/Deck. |
| **NG_Regens Manager 26** | ngregens.org | `architecture` | Memory scan + **server-pushed** offset packs after SI patches — same resilience idea as RVA/signature map. |
| **Cheat Engine FM26 tables** | SortItOutSI / community (e.g. tdg6661 cited by FSS) | `offsets` | Provenance for Fields.cs; pin to game_plugin version. |

---

## Tier D — adjacent (not live RAM core, still useful)

| Item | URL | Steal | Notes |
|------|-----|-------|-------|
| pyscoutfm | PyPI / GitHub | discard for live core | HTML export ratings — not RAM. |
| mickyyy68/fm24-scout | GitHub | architecture (UI) | FM24 Tauri scout from exports — stack cousin, not memory. |
| FM-Arena attribute weight threads | fm-arena.com | offsets/weights | Role scoring evidence, not memory. |
| BepInEx 6 IL2CPP | GitHub | discard-product | How FSS works; FMT product path stays external reader. |

---

## Known recipes (do these, don’t invent)

### R1 — Full-world pointer arrays (&lt;2s class)
1. Find `game_plugin.dll` base in `fm.exe` process.  
2. Locate offset table (`tableRva` for build **or** score-scan slots).  
3. For each needed slot: `read(slotPtr+0x80)` → `{begin,end}`, walk `count=(end-begin)/8`.  
4. People: split by person-type / vtable (Player / Staff / Human…).  
5. **Then** resolve human manager → managed club → Club.Teams for Squad.  

**Canonical open code:** fm-ai-assistent `FmOffsets`.  
**Stable slots:** City 0xF0, Club 0xF8, Competition 0x100, Continent 0x108, Nation 0x110, Currency 0x118, People 0x150, Region 0x160, Stadium 0x168, Team 0x180, Agreement 0x1A0.

### R2 — Field decode (player / person / contract)
Use FMSuperScout `Fields.cs` + FMT `entity-maps/index.json`.  
Already matched: UID, CA/PA, positions, attrs×5, names, nation, DOB, contract ptr, personality pack.  
**Not** matched by UID band: regen/newgen. DB wonderkids (e.g. Yamal `2000256231`) share the ~2.0B UID range with regens — do not use UID ≥ 1.9B as origin law. Face `r-{uid}` is graphics-pack namespace only.  
**T216:** origin = `person+0xD5` (`isDatabaseOrigin`: 1=DB, 0=regen). Validated Yamal-set vs Schalke U19+First Team. `isRegen = (byte==0)`. Face `r-{uid}` and UID ≥1.9B are **not** law. FSS `person+0x18` bit `0x08` = youth team, not newgen. Probe: `npm run probe:player-origin` (`PLAYER_ORIGIN_SKIP_DB=1` for fast squad check).  
Next free wins when ticketed: wage `contract+0x20`, expiry `+0x48`, guide/transfer value, team competition `@0x50`.

### R3 — Managed club/teams (Loop A today)
GlassScout/FMT: human registry signature → managed team → club → `Club.Teams` @+0x18/+0x20, `TeamType` @+0x28.  
Keep until world core lands; do not expand world coverage this way.

### R4 — Patch survival
Maintain build→RVA (or remote pack). Fallback: scored table signature (count ranges). Closed tools often pull offsets online (FMLE, NG_Regens).

---

## FMT internal anchors (already in repo)

| Path | Role |
|------|------|
| `desktop/src-tauri/entity-maps/index.json` | Locked build profile + field status |
| `desktop/src-tauri/src/fm26/` | Process reader, squad path, probes |
| `desktop/src-tauri/src/fm26/player_registry.rs` | Idiom/registry experiments — **not** preferred world path |
| `NOTICE-GlassScout.md` | Upstream attribution |
| `.cursor/rules/fm-live-read.mdc` | Agent law when editing live-read code |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-09-04 | Initial index from live-read research; world-tables-first direction recorded |
