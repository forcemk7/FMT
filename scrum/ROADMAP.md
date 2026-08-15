# Roadmap — what we ship

Tickets and done/ready live in [STATUS.md](./STATUS.md). This file is the **funded product**. Law: [SCOPE.md](./SCOPE.md).

## The product

A **lightweight Genie Scout for hidden attributes**: this club’s **HA + CA** from a Career Save, without installing GS and without loading every player, staff, and stadium.

Tight **mentoring loop**, also usable to plan **youth development** (who is growing, who is out on loan, who can sit in a group).

Must run **in the cloud** (upload save → extract → four tabs). Local `npm run dev` is the same extract contract.

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
| Take **one** Career `.fm` (upload, or copy from SI `games/` into `data/saves`) | Working copy only |
| Read-only open / mmap that copy | Never lock FM autosave |
| Find **this club’s** FT / II / U19 lists | Squad + Loans |
| Pull per player: uid, name, unit, age, pack HA, Det/Lea, CA, in-game today, loan flag | Tabs 1–4 |
| Put **loaned-out** on Loans only; Squad is at-club | Honesty + mentoring pool |
| Stream or partial decompress only as far as those lists need | Expedient |
| When JSON is written: **delete** temp `.fm` / decompress blobs (cloud: always; local: keep the `data/saves` copy the user chose) | Cloud must not store saves |

**Do not**

| Action | Why |
|--------|-----|
| Extract or mmap live `Documents/Sports Interactive/…/games/*.fm` | Locks autosave |
| Write, patch, or round-trip the `.fm` | Not an editor |
| Keep the uploaded `.fm` in cloud storage | Privacy + cost |
| Walk staff, stadiums, world players, tactics, media, graphics | GS’s 15-minute load |
| Full-file decompress “to be safe” after this club is already in hand | Waste |
| Run several full decompresses of the same save at once | T072: one Python, no 5×2GB |
| Require SI `graphics/` for the cloud path | No download, no local FM install |

### 7. Ship shape

- GitHub `forcemk7/FMT`
- Local: clone + `npm run dev` (same extract rules)
- Cloud: upload → extract → discard `.fm`
- Buy Me a Coffee (tip, not Stripe)
- One git commit per ticket (AGENTS.md)

## Not funded

Suggest, HAS ranker/checker/compare as app chrome, editor / write-to-save, FMT→in-game sync, Talent tab, CA/PA columns on Squad, exe, FM27 extract, storing career saves in the cloud.

## Later (notes, not a promise)

- Extract entirely in the browser (no server Python)
- Read mentoring groups back from the save
- CA/PA as Squad columns if Progress is not enough
