# Roadmap — what we ship

Tickets and done/ready live in [STATUS.md](./STATUS.md). This file is the **funded product**. Law: [SCOPE.md](./SCOPE.md).

## The product

A **lightweight Genie Scout for hidden attributes**: this club’s **HA + CA** from a Career Save, without installing GS and without loading every player, staff, and stadium.

Tight **mentoring loop**, also usable to plan **youth development** (who is growing, who is out on loan, who can sit in a group).

Must run **in the cloud** (upload save → extract → four tabs). That means **any** Career Save, not one fitted continue. Local `npm run dev` is the same extract contract.

```
Upload / copy Career Save
  → extract this club only (see Savefile)
  → Squad (HA table, at-club)
  → Loans (honesty + who is out)
  → Progress (CA growth + HA movement)
  → Mentoring (reminder)
  → you create the group in FM
```

Tab order: **Squad | Loans | Mentoring | Progress**

Money: **Buy Me a Coffee**. Optional tip. Nothing is gated.

## Funded features

### 1. Squad

Club-wide HA table for **FT + II + U19 at-club** (loaned-out players are not here).

- Columns: name, unit, age, personality, media, Det / Pro / Pre / Amb / Tem / Lea / Loy / Spo / Con (HAS optional)
- Click a player → filters from their numbers (kid: find mentors; senior: find mentees)
- Edit / loosen floors; missing = `—`
- Group checks: three names become a mentoring unit

**Label:** **Squad** (not Personalities, not Players).

### 2. Loans

Outgoing loans for this club, by unit. **Honesty feature:** a short list is easier to check against FM than 99 at-club names. Also: youth out on loan are part of development planning. Same extract tags as Squad (no second detector).

### 3. Mentoring

Reminder list of units you will create in FM. Add from Squad, list, remove. **No Suggest.** At-club only (not players who are on Loans).

### 4. Progress

Per-player history after extract on a new in-game date.

- **CA points** — who is growing; high growth ⇒ likely high PA ⇒ worth mentoring if personality is poor
- **HA points** — pack + Det/Lea movement; mentoring influence

One extract ⇒ values, empty deltas. Two different game dates ⇒ deltas.

### 5. Cloud

Same four tabs behind a public URL. User uploads a `.fm`. Server runs the extract below, returns roster JSON, **deletes the binary**. No desktop install. Faces from SI graphics are **local-only**; cloud ships without a face pack.

### 6. Savefile (extract contract)

The save is a **read-only input**. Speed comes from doing less, not a faster full dump.

**Do**

| Step | Why |
|------|-----|
| 0. Take **one** Career `.fm` (upload, or copy into `data/saves`) | Working copy only; never live `games/*.fm` |
| 1. Find the **managed club** of this save | Whoever uploaded |
| 2. **Employed players** — that club’s FT, II, U19 job lists → people | Who belongs to the club |
| 3. Those players: **pack** + **CA card**, once each | HA + CA |
| 4. **Contracts** — loan object on those jobs → outgoing | At-club (Squad / Mentoring) vs loaned out (Loans) |
| When JSON is written: **delete** temp `.fm` / decompress blobs (cloud: always; local: keep the chosen `data/saves` copy) | Cloud must not store saves |

**Do not**

| Action | Why |
|--------|-----|
| Extract or mmap live `Documents/Sports Interactive/…/games/*.fm` | Locks autosave |
| Write, patch, or round-trip the `.fm` | Not an editor |
| Keep the uploaded `.fm` in cloud storage | Privacy + cost |
| Walk staff, stadiums, world players, tactics, media, graphics | GS’s 15-minute load |
| Hunt Det/Lea as a third extract, or walk the CA card twice | Same blob; UI splits |
| Hard-wire one Career Save (names, UIDs, byte windows, club 920) | Cloud is any upload; König is a check, not the model |
| Full-file decompress “to be safe” after this club is already in hand | Waste |
| Run several full decompresses of the same save at once | T072: one Python, no 5×2GB |
| Require SI `graphics/` for the cloud path | No download, no local FM install |

### 7. Ship shape

**Launch waits.** No public URL until the owner can upload **any** Career Save locally and see an honest at-club vs loaned split (T086). Sharing on FM Scout comes after that.

- GitHub `forcemk7/FMT`
- **T077:** blocked on T088. No www until local loop: any save + Active not stolen by a finishing extract
- BMC already on the header (`buymeacoffee.com/mrramirez`)
- Local `npm run dev` stays the same extract rules
- One git commit per ticket (AGENTS.md)

## Not funded

Suggest, HAS ranker/checker/compare as app chrome, editor / write-to-save, FMT→in-game sync, Talent tab, favoured-club / scout extract, CA/PA columns on Squad, exe, FM27 extract, storing career saves in the cloud.

## Later (notes, not a promise)

- Extract entirely in the browser (no server Python)
- Read mentoring groups back from the save
- CA/PA as Squad columns if Progress is not enough
- Progress GK vs outfield CA layout (T087) after native roster honesty
- Identity must be honest on any save (T096) before more squad-join recipes
- Player trophy cabinet on profile (T162) — marketable; RE + desk only after Loop A habit and a locked wins object
