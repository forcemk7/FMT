/**
 * Club crests live in repo `data/logos/{clubId}.*` (T056/T058 shape).
 * SI graphics/ is the copy source only — `/api/logos` serves the copies.
 */
import fs from "node:fs";
import path from "node:path";
import type { FirstTeamExtract, FirstTeamPlayer } from "../save/types.ts";

const LOGO_EXTS = [".png", ".jpg", ".jpeg", ".webp"] as const;

export function resolveRepoLogosDir(rootDir: string): string {
  return path.join(rootDir, "data", "logos");
}

export function findCachedLogo(logosDir: string, clubId: number): string | null {
  if (!Number.isFinite(clubId) || clubId <= 0) return null;
  for (const ext of LOGO_EXTS) {
    const p = path.join(logosDir, `${clubId}${ext}`);
    if (fs.existsSync(p)) return p;
  }
  return null;
}

/** Copy SI crest into data/logos/{clubId}{ext}. Skip if already present. */
export function copyLogoIntoRepo(
  srcPath: string,
  logosDir: string,
  clubId: number,
): string {
  fs.mkdirSync(logosDir, { recursive: true });
  const ext = path.extname(srcPath).toLowerCase() || ".png";
  const dest = path.join(logosDir, `${clubId}${ext}`);
  if (fs.existsSync(dest)) return dest;
  fs.copyFileSync(srcPath, dest);
  return dest;
}

export function collectExtractLogoIds(extract: FirstTeamExtract): number[] {
  const ids = new Set<number>();
  const addId = (raw: unknown) => {
    const id = Number(raw);
    if (Number.isFinite(id) && id > 0) ids.add(id);
  };
  const addPlayers = (players: FirstTeamPlayer[] | null | undefined) => {
    for (const player of players ?? []) {
      addId(player.loan?.loanClubId);
      addId(player.loan?.parentClubId);
    }
  };
  addId(extract.clubId);
  addId(extract.reserves?.clubId);
  addPlayers(extract.players);
  addPlayers(extract.reserves?.players);
  addPlayers(extract.u19?.players);
  return [...ids];
}

export function countCachedImages(dir: string): number {
  try {
    return fs
      .readdirSync(dir)
      .filter((name) => /^\d+\.(png|jpe?g|webp)$/i.test(name)).length;
  } catch {
    return 0;
  }
}
