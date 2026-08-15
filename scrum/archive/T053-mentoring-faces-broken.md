---
id: T053
title: INCIDENT — restore Mentoring player faces
status: done
priority: 1
owner: cursor-worker
claimed_at: 2026-08-14
started_at: 2026-08-14
completed_at: 2026-08-14
depends_on: []
---

# T053 — INCIDENT: Mentoring faces missing (initials only)

## Why

**Loop break (behavior):** Mentoring overview’s job is **see who is grouped** (T021: face + name). User on Mentoring: 9 seated players, **only Dennis Seimen** has a photo. Everyone else is a grey square + initial (Kizza, Contreras, Jones, Koné, Radović, Yoan Robert, Miraglia, Itu). Mentee-strip circles are initials too.

Names still work. Identity scan does not. This is a restore of shipped faces, not a new graphics feature.

## Scope

- In: diagnose + restore `/api/faces/:uid` + `bindPlayerFace` so Mentoring **seats**, **peer faces**, and **mentee strip** show the pack photo when a file exists for that uid
- In: same bind path is shared with Progress / Loans — if the fix is in the API or `bindPlayerFace`, those come along; do not rebuild those UIs
- Out: new face pack, Sortitoutsi download, Suggest, HA table, custom overlay, placeholder art redesign

## Acceptance criteria

- [x] Mentoring seats that have a graphics-pack file for that player uid show the photo (not the letter fallback)
- [x] Seimen still shows; at least one current miss (e.g. Kizza / Itu / Yoan Robert) shows if the pack has that uid
- [x] Confirmed miss (no file) still falls back to the initial — do not hang on a spinner
- [x] No `display:none` on the `<img>` before the fetch starts (browsers skip those requests)

## Notes / pointers

- `bindPlayerFace` in `web/main.ts` (~6924). Mentoring: `createMentoringPlayerFace` (~10638), seats ~10878, strip ~9821
- API: `facesApiPlugin` in `vite.config.ts`; index `shared/faces/face-index.ts`
- Seimen hit + everyone else miss ⇒ likely **cutout fast-path vs regen XML**, not a total API death. Compare `GET /api/faces/<seimen-uid>` vs a miss uid. Regen configs `>2MB` are skipped (treated as `face_{uid}.png` dirs) — NGRegens may not use that layout
- Also check: Mentoring re-render `replaceChildren` aborting in-flight fetches; `has-no-face` / `display:none` skip
- Do not invent a new face pipeline

## Progress

- Cause: `NG Regens Newgens Megapack` (config XML only) is indexed before `NGRegens_Newgens_Megapack` (PNGs). First-wins UID map pointed at missing files → 404. Cutout `face_{uid}.png` still served Seimen.
- Shipped: skip config dirs with no image files in `buildFaceIndex`. Same `/api/faces` + `bindPlayerFace` path. Mentoring CSS already keeps `<img>` in layout until miss.
- Verified: `npx vitest run tests/face-index.test.ts` (1 passed). Live index: Seimen cutout HIT; Kizza / Yoan / Itu / Contreras HIT under `NGRegens_Newgens_Megapack`. Missing uid still null.
- Residual: restart `npm run dev` so the faces plugin reloads the index code.
