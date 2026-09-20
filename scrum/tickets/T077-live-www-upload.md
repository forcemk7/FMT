---
id: T077
title: Live www URL — upload save, extract, four tabs
status: blocked
priority: 2
owner: null
claimed_at: null
started_at: null
completed_at: null
depends_on: [T086, T088]
---

# T077 — Live www URL — upload save, extract, four tabs

## Why

Launch waits until extract is honest on any Career Save (T086). Then ship step 1 is the owner using FMT from a public `https://` address, not `npm run dev`. Sharing (FM Scout etc.) comes after that URL exists.

## Scope

- In: host the Vite UI + extract so a browser can **upload one Career `.fm`**, run the existing this-club extract, show **Squad | Loans | Mentoring | Progress**, then **delete** the uploaded binary and temp decompress files
- In: cloud path must **not** read SI `games/` or `graphics/` (no live watch, faces optional / initials OK)
- In: one Python extract at a time (T072). Machine needs enough RAM (~2GB while extract runs)
- Out: FM Scout post, custom domain unless already on the host, Stripe, Suggest, storing `.fm` in object storage, Vercel/Netlify-only (they will time out / OOM this extract)
- Out: T073 rename / T075 strip unless already done — www can ship with current tab labels

## Acceptance criteria

- [ ] Human opens an `https://` URL (Fly/Railway/`*.fly.dev` is enough — not localhost)
- [ ] Upload a real Career Save → extract finishes → Squad shows at-club HA for **that** club (not an empty table). König is not the only save that works
- [ ] Loans / Mentoring / Progress still work
- [ ] After success, the uploaded `.fm` is gone from the server
- [ ] Refresh / second upload does not stack two full decompresses
- [ ] One git commit `T077: …` on FMT/; ticket may say **push** so the host can deploy

## Blockers

- **T088.** Do not ship www until the owner can stay on the save they selected while another slot finishes extracting.
- Host account that can run Docker/Python with **≥2GB RAM** (Fly.io, Railway, or a VPS). Not Vercel.
- HQ pastes the live URL into STATUS when up.

## Notes / pointers

- Extract: `scripts/extract-first-team-fast.py` / Vite `/api` in `vite.config.ts`
- Savefile law: ROADMAP §6 — read-only copy, no live `games/*.fm`, no write-back
- Steal: Sortitoutsi upload → process → don’t keep the file. Not GS’s desktop load.

## Progress

_(worker fills)_
