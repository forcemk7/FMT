import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import readline from "node:readline";

const RECORD_RE =
  /from="([^"]+)"\s+to="graphics\/pictures\/person\/(?:r-)?(\d+)\/portrait"/gi;

const SKIP_PACK_RE = /kit|logo|badge|wallpaper|background|icon/i;

/** Known FM26 portrait packs (under …/graphics/). */
export const PORTRAIT_PACK_DIRS = [
  "Cutout_Player_Faces_Megapack_2026.08",
  "NGRegens_Newgens_Megapack",
] as const;

export type FaceIndex = {
  graphicsRoot: string;
  /** uid → absolute image path */
  byUid: Map<number, string>;
  /** Direct face_{uid}.* folders (megapack convention; skips huge XML parse). */
  faceDirs: string[];
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

function isPortraitConfig(configPath: string): boolean {
  const lower = configPath.replace(/\\/g, "/").toLowerCase();
  if (lower.includes("/iconfaces/") || lower.includes("/icons/")) return false;
  return true;
}

/** Shallow discovery of pack config.xml files (avoids readdir on huge face folders). */
export function findFacepackConfigs(graphicsRoot: string): string[] {
  const configs: string[] = [];
  const seen = new Set<string>();
  const add = (p: string) => {
    const n = path.normalize(p);
    if (seen.has(n) || !fs.existsSync(n)) return;
    if (!isPortraitConfig(n)) return;
    seen.add(n);
    configs.push(n);
  };

  let packs: fs.Dirent[];
  try {
    packs = fs.readdirSync(graphicsRoot, { withFileTypes: true });
  } catch {
    return configs;
  }

  for (const pack of packs) {
    if (!pack.isDirectory()) continue;
    if (SKIP_PACK_RE.test(pack.name)) continue;
    const packPath = path.join(graphicsRoot, pack.name);
    add(path.join(packPath, "faces", "config.xml"));
    add(path.join(packPath, "config.xml"));

    let subs: fs.Dirent[];
    try {
      subs = fs.readdirSync(packPath, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const s of subs) {
      if (!s.isDirectory()) continue;
      add(path.join(packPath, s.name, "config.xml"));
      add(path.join(packPath, s.name, "faces", "config.xml"));
    }
  }

  return configs;
}

/** True when the folder has a portrait file (not config-only XML). */
function dirHasImageFiles(dir: string): boolean {
  let dh: fs.Dir;
  try {
    dh = fs.opendirSync(dir);
  } catch {
    return false;
  }
  try {
    for (;;) {
      const e = dh.readSync();
      if (!e) return false;
      if (!e.isFile()) continue;
      if (/\.(png|jpe?g|webp)$/i.test(e.name)) return true;
    }
  } finally {
    dh.closeSync();
  }
}

export function discoverFaceDirs(graphicsRoot: string): string[] {
  const dirs: string[] = [];
  let packs: fs.Dirent[];
  try {
    packs = fs.readdirSync(graphicsRoot, { withFileTypes: true });
  } catch {
    return dirs;
  }
  for (const pack of packs) {
    if (!pack.isDirectory()) continue;
    if (SKIP_PACK_RE.test(pack.name)) continue;
    const facesDir = path.join(graphicsRoot, pack.name, "faces");
    const config = path.join(facesDir, "config.xml");
    if (!fs.existsSync(config)) continue;
    try {
      if (fs.statSync(config).size > 2_000_000) dirs.push(facesDir);
    } catch {
      // ignore
    }
  }
  return dirs;
}

/**
 * Build a UID→image index.
 * Large face_* megapack XMLs are skipped — those resolve via face_{uid}.png on demand.
 * Regen ethnicity configs are parsed for from/to mappings (no existsSync per row).
 * Config-only duplicate packs (XML, no PNGs) are skipped so they cannot steal UIDs.
 */
export async function buildFaceIndex(
  graphicsRoot: string = resolveDefaultGraphicsRoot(),
): Promise<FaceIndex> {
  const byUid = new Map<number, string>();
  const faceDirs = discoverFaceDirs(graphicsRoot);
  const configs = findFacepackConfigs(graphicsRoot);
  const faceDirSet = new Set(faceDirs.map((d) => path.normalize(d)));

  for (const configPath of configs) {
    const dir = path.dirname(configPath);
    if (faceDirSet.has(path.normalize(dir))) continue;
    if (!dirHasImageFiles(dir)) continue;

    const stream = fs.createReadStream(configPath, { encoding: "utf8" });
    const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });
    for await (const line of rl) {
      RECORD_RE.lastIndex = 0;
      let m: RegExpExecArray | null;
      while ((m = RECORD_RE.exec(line))) {
        const fromName = m[1]!;
        const uid = Number(m[2]);
        if (!Number.isFinite(uid)) continue;
        if (/^iconface_/i.test(fromName)) continue;
        if (byUid.has(uid)) continue;
        byUid.set(uid, path.join(dir, `${fromName}.png`));
      }
    }
  }

  return {
    graphicsRoot,
    byUid,
    faceDirs,
    configCount: configs.length,
  };
}

/** Instant cutout-only index (no XML parse) — enough for real-face megapacks. */
export function buildCutoutFaceIndex(
  graphicsRoot: string = resolveDefaultGraphicsRoot(),
): FaceIndex {
  return {
    graphicsRoot,
    byUid: new Map(),
    faceDirs: discoverFaceDirs(graphicsRoot),
    configCount: 0,
  };
}

export function resolveFacePath(index: FaceIndex, uid: number): string | null {
  // Real cutout megapack first (face_{uid}.png), then regen XML mappings.
  for (const dir of index.faceDirs) {
    for (const name of [`face_${uid}.png`, `face_${uid}.jpg`, `${uid}.png`]) {
      const p = path.join(dir, name);
      if (fs.existsSync(p)) {
        index.byUid.set(uid, p);
        return p;
      }
    }
  }

  const cached = index.byUid.get(uid);
  if (cached) {
    if (fs.existsSync(cached)) return cached;
    const base = path.basename(cached, path.extname(cached));
    const dir = path.dirname(cached);
    for (const ext of [".jpg", ".jpeg", ".webp"]) {
      const p = path.join(dir, base + ext);
      if (fs.existsSync(p)) {
        index.byUid.set(uid, p);
        return p;
      }
    }
  }

  return null;
}

export function contentTypeForImage(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".webp") return "image/webp";
  if (ext === ".gif") return "image/gif";
  return "image/png";
}
