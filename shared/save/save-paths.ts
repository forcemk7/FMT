/**
 * Career .fm files: extract from repo `data/saves` only.
 * Live Sports Interactive/…/games/*.fm may be watched, stat'd, and copied
 * into data/saves — never extracted (locks FM autosave).
 * SI graphics/ for faces and logos is unrelated and allowed.
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const LIVE_GAMES_SAVE_RE =
  /[/\\]sports interactive[/\\][^/\\]+[/\\]games[/\\]/i;

export const FM_GAME_TITLE = "Football Manager 26";

/** Live FM Career Save folder — watch/stat/copy source only. */
export function resolveFmGamesDir(): string {
  return path.join(
    os.homedir(),
    "Documents",
    "Sports Interactive",
    FM_GAME_TITLE,
    "games",
  );
}

export function resolveRepoSavesDir(rootDir: string): string {
  return path.join(rootDir, "data", "saves");
}

/** Directories searched for extract. Live FM games/ is never on this list. */
export function saveSearchDirs(rootDir: string): string[] {
  return [resolveRepoSavesDir(rootDir)];
}

/** True when `filePath` is a .fm under Sports Interactive/…/games/. */
export function isLiveFmGamesSavePath(filePath: string): boolean {
  const lower = filePath.toLowerCase();
  return LIVE_GAMES_SAVE_RE.test(filePath) && lower.endsWith(".fm");
}

export function assertNotLiveFmGamesSave(filePath: string): void {
  if (isLiveFmGamesSavePath(filePath)) {
    throw new Error(
      "Refusing Sports Interactive/games/*.fm — copy the Career Save into data/saves",
    );
  }
}

export function listFmSavePaths(rootDir: string): string[] {
  const files: string[] = [];
  const seen = new Set<string>();
  for (const dir of saveSearchDirs(rootDir)) {
    if (!fs.existsSync(dir)) continue;
    for (const name of fs.readdirSync(dir)) {
      if (!name.toLowerCase().endsWith(".fm")) continue;
      const full = path.join(dir, name);
      assertNotLiveFmGamesSave(full);
      const key = path.normalize(full).toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      files.push(full);
    }
  }
  return files;
}

/** FM manual/backup copies: `Career (v02).fm` — never auto-copied. */
export function isFmBackupVersionName(saveName: string): boolean {
  return /\s\(v\d+\)\.fm$/i.test(path.basename(saveName));
}

/**
 * Dest path in data/saves for a basename, even if the file does not exist yet.
 * Does not create the file. Versioned (v02) names are refused.
 */
export function repoSaveDestPath(
  saveName: string,
  rootDir: string,
): string | null {
  const base = path.basename(saveName);
  if (!base.toLowerCase().endsWith(".fm")) return null;
  if (isFmBackupVersionName(base)) return null;
  return path.join(resolveRepoSavesDir(rootDir), base);
}

/**
 * True when dest is already a copy of this live snapshot.
 * Dest mtime is copy time, so it should be >= live mtime at the same size.
 * Skip recopy in that case — a recopy would bump dest mtime and re-extract forever.
 */
export function destCoversLiveSnapshot(
  destPath: string,
  live: { mtimeMs: number; size: number },
): boolean {
  try {
    if (!fs.existsSync(destPath)) return false;
    const dest = fs.statSync(destPath);
    return dest.size === live.size && dest.mtimeMs >= live.mtimeMs;
  } catch {
    return false;
  }
}

/**
 * Copy a live games/*.fm write into data/saves only when it is already there
 * or it is the selected FMT save. Versioned (v02) and other careers stay out.
 */
export function shouldCopyLiveFmSave(
  liveName: string,
  rootDir: string,
  selectedSaveName?: string | null,
): boolean {
  const base = path.basename(liveName);
  if (!base.toLowerCase().endsWith(".fm")) return false;
  if (isFmBackupVersionName(base)) return false;
  if (resolveFmSaveByName(base, rootDir)) return true;
  if (!selectedSaveName) return false;
  return path.basename(selectedSaveName).toLowerCase() === base.toLowerCase();
}

/** Resolve a save by filename (case-insensitive). Returns on-disk casing. */
export function resolveFmSaveByName(
  saveName: string,
  rootDir: string,
): string | null {
  const base = path.basename(saveName);
  if (!base.toLowerCase().endsWith(".fm")) return null;

  const want = base.toLowerCase();
  for (const dir of saveSearchDirs(rootDir)) {
    if (!fs.existsSync(dir)) continue;
    for (const name of fs.readdirSync(dir)) {
      if (name.toLowerCase() === want) {
        const full = path.join(dir, name);
        assertNotLiveFmGamesSave(full);
        return full;
      }
    }
  }
  return null;
}

export type SaveDiskStat = {
  saveName: string;
  path: string;
  mtimeMs: number;
  size: number;
};

export function statFmSave(
  saveName: string,
  rootDir: string,
): SaveDiskStat | null {
  const filePath = resolveFmSaveByName(saveName, rootDir);
  if (!filePath) return null;
  const st = fs.statSync(filePath);
  return {
    saveName: path.basename(filePath),
    path: filePath,
    mtimeMs: st.mtimeMs,
    size: st.size,
  };
}

/**
 * FM touches the file on Save click, then can keep writing for a long time.
 * Prefer a long delay over a silent corrupt extract.
 * Stat-only — allowed on the live games path.
 */
export const SAVE_SETTLE_POLL_MS = 2000;
/** Size/mtime must stay unchanged this long before we treat the write as finished. */
export const SAVE_SETTLE_STABLE_MS = 15_000;
/** Cap how long we wait for a stable write (auto-sync). */
export const SAVE_SETTLE_MAX_MS = 180_000;
/**
 * Quiet period after the *last* change event before settle-checking.
 * 60s keeps us clear of slow FM saves; each new write resets this timer.
 */
export const SAVE_WATCH_DEBOUNCE_MS = 60_000;

const COPY_RETRIES = 5;
const COPY_RETRY_MS = 2000;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isBusyFsError(err: unknown): boolean {
  const code = (err as NodeJS.ErrnoException)?.code;
  return (
    code === "EBUSY" ||
    code === "EPERM" ||
    code === "EACCES" ||
    code === "EAGAIN" ||
    code === "EIO"
  );
}

/**
 * Poll until `mtimeMs`+`size` are unchanged for `stableMs`, or until `maxMs`.
 * Stat only — safe on the live FM games path. Do not extract that path.
 */
export async function waitForFileStable(
  filePath: string,
  options?: {
    pollMs?: number;
    stableMs?: number;
    maxMs?: number;
  },
): Promise<{ mtimeMs: number; size: number } | null> {
  const pollMs = options?.pollMs ?? SAVE_SETTLE_POLL_MS;
  const stableMs = options?.stableMs ?? SAVE_SETTLE_STABLE_MS;
  const maxMs = options?.maxMs ?? SAVE_SETTLE_MAX_MS;
  const started = Date.now();
  let last: { mtimeMs: number; size: number } | null = null;
  let stableSince = 0;

  while (Date.now() - started < maxMs) {
    try {
      if (!fs.existsSync(filePath)) return null;
      const st = fs.statSync(filePath);
      const cur = { mtimeMs: st.mtimeMs, size: st.size };
      if (
        last &&
        cur.mtimeMs === last.mtimeMs &&
        cur.size === last.size
      ) {
        if (Date.now() - stableSince >= stableMs) return cur;
      } else {
        last = cur;
        stableSince = Date.now();
      }
    } catch {
      // mid-write / locked — keep waiting
      last = null;
      stableSince = 0;
    }
    await sleep(pollMs);
  }
  return last;
}

function streamCopyFile(src: string, dest: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const ins = fs.createReadStream(src);
    const out = fs.createWriteStream(dest);
    const fail = (err: Error) => {
      ins.destroy();
      out.destroy();
      reject(err);
    };
    ins.on("error", fail);
    out.on("error", fail);
    out.on("finish", () => resolve());
    ins.pipe(out);
  });
}

/**
 * Short-lived copy of a live SI games/*.fm into data/saves.
 * Source must be the live folder; dest must not be. Closes handles before return.
 */
export async function copyLiveFmSaveToRepo(
  livePath: string,
  destPath: string,
  options?: { retries?: number; retryMs?: number },
): Promise<{ mtimeMs: number; size: number }> {
  if (!isLiveFmGamesSavePath(livePath)) {
    throw new Error(
      "copyLiveFmSaveToRepo: source must be Sports Interactive/games/*.fm",
    );
  }
  assertNotLiveFmGamesSave(destPath);
  if (!destPath.toLowerCase().endsWith(".fm")) {
    throw new Error("copyLiveFmSaveToRepo: dest must be a .fm file");
  }

  const retries = options?.retries ?? COPY_RETRIES;
  const retryMs = options?.retryMs ?? COPY_RETRY_MS;
  const tmpPath = `${destPath}.copying`;
  fs.mkdirSync(path.dirname(destPath), { recursive: true });

  let lastErr: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      await streamCopyFile(livePath, tmpPath);
      try {
        fs.unlinkSync(destPath);
      } catch {
        // dest may not exist yet
      }
      fs.renameSync(tmpPath, destPath);
      const st = fs.statSync(destPath);
      return { mtimeMs: st.mtimeMs, size: st.size };
    } catch (err) {
      lastErr = err;
      try {
        fs.unlinkSync(tmpPath);
      } catch {
        // ignore
      }
      if (!isBusyFsError(err) || attempt === retries) break;
      await sleep(retryMs);
    }
  }
  throw lastErr instanceof Error
    ? lastErr
    : new Error("copyLiveFmSaveToRepo failed");
}
