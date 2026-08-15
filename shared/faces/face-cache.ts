/**
 * Roster portraits live in repo `data/faces/{uid}.*` (T056 shape).
 * SI graphics/ is the copy source only — `/api/faces` serves the copies.
 */
import fs from "node:fs";
import path from "node:path";
import type { FirstTeamExtract } from "../save/types.ts";

const FACE_EXTS = [".png", ".jpg", ".jpeg", ".webp"] as const;

export function resolveRepoFacesDir(rootDir: string): string {
  return path.join(rootDir, "data", "faces");
}

export function findCachedFace(facesDir: string, uid: number): string | null {
  if (!Number.isFinite(uid) || uid <= 0) return null;
  for (const ext of FACE_EXTS) {
    const p = path.join(facesDir, `${uid}${ext}`);
    if (fs.existsSync(p)) return p;
  }
  return null;
}

/** Copy SI portrait into data/faces/{uid}{ext}. Skip if already present. */
export function copyFaceIntoRepo(
  srcPath: string,
  facesDir: string,
  uid: number,
): string {
  fs.mkdirSync(facesDir, { recursive: true });
  const ext = path.extname(srcPath).toLowerCase() || ".png";
  const dest = path.join(facesDir, `${uid}${ext}`);
  if (fs.existsSync(dest)) return dest;
  fs.copyFileSync(srcPath, dest);
  return dest;
}

export function collectExtractFaceUids(extract: FirstTeamExtract): number[] {
  const uids = new Set<number>();
  const add = (players: { uid?: number }[] | null | undefined) => {
    for (const player of players ?? []) {
      const uid = Number(player.uid);
      if (Number.isFinite(uid) && uid > 0) uids.add(uid);
    }
  };
  add(extract.players);
  add(extract.reserves?.players);
  add(extract.u19?.players);
  return [...uids];
}
