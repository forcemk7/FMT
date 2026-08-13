/**
 * Club logo resolve from TCM Logos megapack (FM graphics folder).
 *
 * Layout (nested under graphics/TCM_Logos_Megapack_*):
 *   Men or Women / region / ... / Clubs / config.xml
 *   Clubs/TCM1_<clubId>.png maps to graphics/pictures/club/<clubId>/logo
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import readline from "node:readline";

const RECORD_RE =
  /from="TCM\d+_(\d+)"\s+to="graphics\/pictures\/club\/\1\/logo"/gi;

const PACK_NAME_RE = /^TCM_Logos_Megapack/i;

export type LogoIndex = {
  graphicsRoot: string;
  packRoot: string | null;
  /** clubId → absolute PNG/JPG path */
  byClubId: Map<number, string>;
  /** Clubs folders for on-demand TCM1_<id>.png lookup */
  clubDirs: string[];
  configCount: number;
};

export function resolveDefaultGraphicsRoot(): string {
  return path.join(
    os.homedir(),
    "Documents",
    "Sports Interactive",
    "Football Manager 26",
    "graphics",
  );
}

/** Prefer newest TCM_Logos_Megapack_* under graphics. */
export function findLogosPackRoot(graphicsRoot: string): string | null {
  let packs: fs.Dirent[];
  try {
    packs = fs.readdirSync(graphicsRoot, { withFileTypes: true });
  } catch {
    return null;
  }
  const matches = packs
    .filter((d) => d.isDirectory() && PACK_NAME_RE.test(d.name))
    .map((d) => path.join(graphicsRoot, d.name))
    .sort((a, b) => b.localeCompare(a));
  return matches[0] ?? null;
}

/** Collect …/Clubs directories that contain a config.xml (shallow walk). */
export function discoverClubLogoDirs(packRoot: string): string[] {
  const dirs: string[] = [];
  const stack = [packRoot];
  while (stack.length > 0) {
    const cur = stack.pop()!;
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(cur, { withFileTypes: true });
    } catch {
      continue;
    }
    const base = path.basename(cur);
    if (base === "Clubs" || base === "normal") {
      const cfg = path.join(cur, "config.xml");
      if (fs.existsSync(cfg)) {
        dirs.push(cur);
        continue; // don't descend into huge PNG folders
      }
    }
    for (const e of entries) {
      if (!e.isDirectory()) continue;
      // Skip competition-only trees when named clearly
      if (/^Competitions$/i.test(e.name)) continue;
      stack.push(path.join(cur, e.name));
    }
  }
  return dirs;
}

export async function buildLogoIndex(
  graphicsRoot: string = resolveDefaultGraphicsRoot(),
): Promise<LogoIndex> {
  const packRoot = findLogosPackRoot(graphicsRoot);
  const byClubId = new Map<number, string>();
  if (!packRoot) {
    return {
      graphicsRoot,
      packRoot: null,
      byClubId,
      clubDirs: [],
      configCount: 0,
    };
  }

  const clubDirs = discoverClubLogoDirs(packRoot);
  let configCount = 0;

  for (const dir of clubDirs) {
    const configPath = path.join(dir, "config.xml");
    if (!fs.existsSync(configPath)) continue;
    configCount += 1;
    const stream = fs.createReadStream(configPath, { encoding: "utf8" });
    const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });
    for await (const line of rl) {
      RECORD_RE.lastIndex = 0;
      let m: RegExpExecArray | null;
      while ((m = RECORD_RE.exec(line))) {
        const clubId = Number(m[1]);
        if (!Number.isFinite(clubId) || byClubId.has(clubId)) continue;
        // Clubs live beside config as TCM1_<id>.png (existence checked on serve).
        byClubId.set(clubId, path.join(dir, `TCM1_${clubId}.png`));
      }
    }
  }

  return {
    graphicsRoot,
    packRoot,
    byClubId,
    clubDirs,
    configCount,
  };
}

/** Fast stub before async XML parse finishes — on-demand dir scan only. */
export function buildLogoIndexStub(
  graphicsRoot: string = resolveDefaultGraphicsRoot(),
): LogoIndex {
  const packRoot = findLogosPackRoot(graphicsRoot);
  return {
    graphicsRoot,
    packRoot,
    byClubId: new Map(),
    clubDirs: packRoot ? discoverClubLogoDirs(packRoot) : [],
    configCount: 0,
  };
}

export function resolveLogoPath(index: LogoIndex, clubId: number): string | null {
  if (!Number.isFinite(clubId) || clubId <= 0) return null;

  const cached = index.byClubId.get(clubId);
  if (cached && fs.existsSync(cached)) return cached;

  for (const dir of index.clubDirs) {
    for (const name of [
      `TCM1_${clubId}.png`,
      `TCM1_${clubId}.jpg`,
      `${clubId}.png`,
    ]) {
      const p = path.join(dir, name);
      if (fs.existsSync(p)) {
        index.byClubId.set(clubId, p);
        return p;
      }
    }
  }

  return null;
}

export { contentTypeForImage } from "../faces/face-index.ts";
