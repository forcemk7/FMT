import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, type Plugin } from "vite";
import {
  buildCutoutFaceIndex,
  buildFaceIndex,
  contentTypeForImage,
  resolveDefaultGraphicsRoot,
  resolveFacePath,
  type FaceIndex,
} from "./shared/faces/face-index.ts";
import {
  collectExtractFaceUids,
  copyFaceIntoRepo,
  findCachedFace,
  resolveRepoFacesDir,
} from "./shared/faces/face-cache.ts";
import {
  buildLogoIndex,
  buildLogoIndexStub,
  resolveLogoPath,
  type LogoIndex,
} from "./shared/logos/logo-index.ts";
import {
  collectExtractLogoIds,
  copyLogoIntoRepo,
  countCachedImages,
  findCachedLogo,
  resolveRepoLogosDir,
} from "./shared/logos/logo-cache.ts";
import {
  emptyHistoryStore,
  normalizeHistoryStore,
  playerCount,
  type HistoryStore,
} from "./shared/history-store.ts";
import { extractFirstTeam } from "./shared/save/extract-first-team.ts";
import { extractManagedIdentity } from "./shared/save/extract-managed-team.ts";
import { extractFavouredClubScouts } from "./shared/save/extract-favoured-scouts.ts";
import { createExtractGate } from "./shared/save/extract-gate.ts";
import { killStaleExtractPid } from "./shared/save/extract-child.ts";
import {
  cleanupWorkingFm,
  copyLiveFmSaveToRepo,
  destCoversLiveSnapshot,
  isFmBackupVersionName,
  repoSaveDestPath,
  resolveFmGamesDir,
  resolveFmSaveByName,
  resolveRepoSavesDir,
  resolveWorkingUploadsDir,
  SAVE_WATCH_DEBOUNCE_MS,
  shouldCopyLiveFmSave,
  statFmSave,
  waitForFileStable,
} from "./shared/save/save-paths.ts";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)));
const historyPath = path.join(rootDir, "data", "history.json");
const historyBakPath = path.join(rootDir, "data", "history.json.bak");
const repoFacesDir = resolveRepoFacesDir(rootDir);
const repoLogosDir = resolveRepoLogosDir(rootDir);

let faceIndex: FaceIndex | null = null;
let faceIndexPromise: Promise<FaceIndex> | null = null;
/** Cutout dirs only — available immediately while regen XML parses. */
let cutoutIndex: FaceIndex | null = null;

let logoIndex: LogoIndex | null = null;
let logoIndexPromise: Promise<LogoIndex> | null = null;
let logoStub: LogoIndex | null = null;

function getCutoutIndex(): FaceIndex {
  if (!cutoutIndex) {
    cutoutIndex = buildCutoutFaceIndex(resolveDefaultGraphicsRoot());
  }
  return cutoutIndex;
}

function resetFaceIndex(): void {
  faceIndex = null;
  faceIndexPromise = null;
  cutoutIndex = null;
}

function ensureFaceIndex(force = false): Promise<FaceIndex> {
  if (force) resetFaceIndex();
  if (faceIndex) return Promise.resolve(faceIndex);
  if (!faceIndexPromise) {
    const root = resolveDefaultGraphicsRoot();
    // Serve cutouts immediately while the full regen map builds.
    cutoutIndex = buildCutoutFaceIndex(root);
    faceIndexPromise = buildFaceIndex(root)
      .then((idx) => {
        faceIndex = idx;
        cutoutIndex = {
          graphicsRoot: idx.graphicsRoot,
          byUid: new Map(),
          faceDirs: idx.faceDirs,
          configCount: idx.configCount,
        };
        console.info(
          `[fmt faces] indexed ${idx.byUid.size} regen + ${idx.faceDirs.length} cutout dir(s) under ${idx.graphicsRoot}`,
        );
        if (idx.faceDirs[0]) {
          console.info(`[fmt faces] cutout: ${idx.faceDirs[0]}`);
        }
        return idx;
      })
      .catch((err) => {
        faceIndexPromise = null;
        throw err;
      });
  }
  return faceIndexPromise;
}

function resolveFacePathForRequest(uid: number): string | null {
  // Fast path: cutout megapack never needs the regen XML index.
  const cutoutHit = resolveFacePath(getCutoutIndex(), uid);
  if (cutoutHit) return cutoutHit;
  if (faceIndex) return resolveFacePath(faceIndex, uid);
  return null;
}

/** Copy SI portrait into data/faces. Returns the repo path, or null if no pack file. */
async function ensureRepoFace(uid: number): Promise<string | null> {
  const cached = findCachedFace(repoFacesDir, uid);
  if (cached) return cached;
  let src = resolveFacePathForRequest(uid);
  if (!src) {
    const idx = await ensureFaceIndex();
    src = resolveFacePath(idx, uid);
  }
  if (!src) return null;
  return copyFaceIntoRepo(src, repoFacesDir, uid);
}

async function extractRosterFaces(uids: number[]): Promise<void> {
  const missing = uids.filter((uid) => !findCachedFace(repoFacesDir, uid));
  if (missing.length === 0) return;
  let copied = 0;
  for (const uid of missing) {
    const dest = await ensureRepoFace(uid);
    if (dest) copied += 1;
  }
  console.info(
    `[fmt faces] extracted ${copied}/${missing.length} portraits into ${repoFacesDir}`,
  );
}

async function ensureRepoLogo(clubId: number): Promise<string | null> {
  const cached = findCachedLogo(repoLogosDir, clubId);
  if (cached) return cached;
  let src = resolveLogoPathForRequest(clubId);
  if (!src) {
    const idx = await ensureLogoIndex();
    src = resolveLogoPath(idx, clubId);
  }
  if (!src) return null;
  return copyLogoIntoRepo(src, repoLogosDir, clubId);
}

async function extractRosterLogos(clubIds: number[]): Promise<void> {
  const missing = clubIds.filter((id) => !findCachedLogo(repoLogosDir, id));
  if (missing.length === 0) return;
  let copied = 0;
  for (const clubId of missing) {
    const dest = await ensureRepoLogo(clubId);
    if (dest) copied += 1;
  }
  console.info(
    `[fmt logos] extracted ${copied}/${missing.length} crests into ${repoLogosDir}`,
  );
}

function getLogoStub(): LogoIndex {
  if (!logoStub) {
    logoStub = buildLogoIndexStub(resolveDefaultGraphicsRoot());
  }
  return logoStub;
}

function resetLogoIndex(): void {
  logoIndex = null;
  logoIndexPromise = null;
  logoStub = null;
}

function ensureLogoIndex(force = false): Promise<LogoIndex> {
  if (force) resetLogoIndex();
  if (logoIndex) return Promise.resolve(logoIndex);
  if (!logoIndexPromise) {
    const root = resolveDefaultGraphicsRoot();
    logoStub = buildLogoIndexStub(root);
    logoIndexPromise = buildLogoIndex(root)
      .then((idx) => {
        logoIndex = idx;
        logoStub = idx;
        console.info(
          `[fmt logos] indexed ${idx.byClubId.size} club logos · ${idx.configCount} config(s)` +
            (idx.packRoot ? ` · ${path.basename(idx.packRoot)}` : ""),
        );
        return idx;
      })
      .catch((err) => {
        logoIndexPromise = null;
        throw err;
      });
  }
  return logoIndexPromise;
}

function resolveLogoPathForRequest(clubId: number): string | null {
  if (logoIndex) return resolveLogoPath(logoIndex, clubId);
  return resolveLogoPath(getLogoStub(), clubId);
}

function logosApiPlugin(): Plugin {
  return {
    name: "fmt-logos-api",
    configureServer(server) {
      fs.mkdirSync(repoLogosDir, { recursive: true });
      server.middlewares.use(async (req, res, next) => {
        const url = req.url?.split("?")[0] ?? "";
        if (!url.startsWith("/api/logos")) {
          next();
          return;
        }

        try {
          if (req.method === "GET" && url === "/api/logos/status") {
            sendJson(res, 200, {
              logosDir: repoLogosDir,
              cached: countCachedImages(repoLogosDir),
              ready: true,
            });
            return;
          }

          if (req.method === "POST" && url === "/api/logos/refresh") {
            const t0 = Date.now();
            const idx = await ensureLogoIndex(true);
            sendJson(res, 200, {
              refreshed: true,
              elapsedMs: Date.now() - t0,
              mapped: idx.byClubId.size,
              clubDirs: idx.clubDirs.length,
              configCount: idx.configCount,
              packRoot: idx.packRoot,
            });
            return;
          }

          const match = /^\/api\/logos\/(\d+)$/.exec(url);
          if (req.method === "GET" && match) {
            const clubId = Number(match[1]);
            const filePath = await ensureRepoLogo(clubId);
            if (!filePath) {
              res.statusCode = 404;
              res.setHeader("Cache-Control", "no-store");
              res.end();
              return;
            }
            const stat = fs.statSync(filePath);
            const etag = `"${stat.size}-${Math.trunc(stat.mtimeMs)}"`;
            const inm = req.headers["if-none-match"];
            if (inm && inm === etag) {
              res.statusCode = 304;
              res.setHeader("ETag", etag);
              res.end();
              return;
            }
            res.statusCode = 200;
            res.setHeader("Content-Type", contentTypeForImage(filePath));
            res.setHeader("Cache-Control", "public, max-age=86400");
            res.setHeader("ETag", etag);
            fs.createReadStream(filePath).pipe(res);
            return;
          }

          res.statusCode = 404;
          res.end();
        } catch (error) {
          res.statusCode = 500;
          res.setHeader("Content-Type", "application/json");
          res.end(
            JSON.stringify({
              error: error instanceof Error ? error.message : "Logo API error",
            }),
          );
        }
      });
    },
  };
}

function facesApiPlugin(): Plugin {
  return {
    name: "fmt-faces-api",
    configureServer(server) {
      fs.mkdirSync(repoFacesDir, { recursive: true });
      server.middlewares.use(async (req, res, next) => {
        const url = req.url?.split("?")[0] ?? "";
        if (!url.startsWith("/api/faces")) {
          next();
          return;
        }

        try {
          if (req.method === "GET" && url === "/api/faces/status") {
            sendJson(res, 200, {
              facesDir: repoFacesDir,
              cached: countCachedImages(repoFacesDir),
              ready: true,
            });
            return;
          }

          if (req.method === "POST" && url === "/api/faces/refresh") {
            const t0 = Date.now();
            const idx = await ensureFaceIndex(true);
            sendJson(res, 200, {
              refreshed: true,
              elapsedMs: Date.now() - t0,
              mapped: idx.byUid.size,
              faceDirs: idx.faceDirs.length,
              configCount: idx.configCount,
            });
            return;
          }

          const match = /^\/api\/faces\/(\d+)$/.exec(url);
          if (req.method === "GET" && match) {
            const uid = Number(match[1]);
            const filePath = await ensureRepoFace(uid);
            if (!filePath) {
              res.statusCode = 404;
              res.setHeader("Cache-Control", "no-store");
              res.end();
              return;
            }
            const stat = fs.statSync(filePath);
            const etag = `"${stat.size}-${Math.trunc(stat.mtimeMs)}"`;
            const inm = req.headers["if-none-match"];
            if (inm && inm === etag) {
              res.statusCode = 304;
              res.setHeader("ETag", etag);
              res.setHeader("Cache-Control", "no-cache");
              res.end();
              return;
            }
            res.statusCode = 200;
            res.setHeader("Content-Type", contentTypeForImage(filePath));
            res.setHeader("Last-Modified", stat.mtime.toUTCString());
            res.setHeader("ETag", etag);
            res.setHeader("Cache-Control", "no-cache");
            fs.createReadStream(filePath).pipe(res);
            return;
          }

          sendJson(res, 404, { error: "Not found" });
        } catch (error) {
          if (!res.headersSent) {
            sendJson(res, 500, {
              error:
                error instanceof Error ? error.message : "Faces API error",
            });
          }
        }
      });
    },
  };
}

function readStore(): HistoryStore {
  if (!fs.existsSync(historyPath)) {
    const store = emptyHistoryStore();
    writeStore(store);
    return store;
  }
  try {
    const raw = JSON.parse(fs.readFileSync(historyPath, "utf8")) as unknown;
    const { store, migrated } = normalizeHistoryStore(raw);
    if (migrated) {
      if (!fs.existsSync(historyBakPath)) {
        fs.copyFileSync(historyPath, historyBakPath);
      }
      writeStore(store);
    }
    return store;
  } catch {
    throw new Error("Failed to parse data/history.json");
  }
}

function writeStore(store: HistoryStore) {
  fs.mkdirSync(path.dirname(historyPath), { recursive: true });
  fs.writeFileSync(historyPath, `${JSON.stringify(store, null, 2)}\n`, "utf8");
}

function readBody(req: import("http").IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (chunk) => chunks.push(Buffer.from(chunk)));
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

function sendJson(
  res: import("http").ServerResponse,
  status: number,
  body: unknown,
) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.end(JSON.stringify(body));
}

function historyApiPlugin(): Plugin {
  return {
    name: "fmt-history-api",
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const url = req.url?.split("?")[0] ?? "";
        if (!url.startsWith("/api/history")) {
          next();
          return;
        }

        try {
          if (req.method === "GET" && url === "/api/history") {
            sendJson(res, 200, readStore());
            return;
          }

          if (req.method === "PUT" && url === "/api/history") {
            const raw = await readBody(req);
            const parsed = JSON.parse(raw) as unknown;
            const { store } = normalizeHistoryStore(parsed);
            if (!Array.isArray(store.saves)) {
              sendJson(res, 400, { error: "saves must be an array" });
              return;
            }

            let existing: HistoryStore = emptyHistoryStore();
            try {
              existing = readStore();
            } catch {
              // allow write
            }

            const allowEmpty =
              req.headers["x-fmt-allow-empty"] === "1" ||
              req.headers["x-fmt-allow-empty"] === "true";
            const incomingPlayers = playerCount(store);
            const existingPlayers = playerCount(existing);

            if (
              !allowEmpty &&
              existingPlayers > 0 &&
              (store.saves.length === 0 || incomingPlayers === 0)
            ) {
              sendJson(res, 409, {
                error:
                  "Refusing to overwrite history with an empty store. Use Clear, or send x-fmt-allow-empty: 1.",
              });
              return;
            }

            writeStore(store);
            sendJson(res, 200, store);
            return;
          }

          if (req.method === "DELETE" && url === "/api/history") {
            const store = emptyHistoryStore();
            writeStore(store);
            sendJson(res, 200, store);
            return;
          }

          sendJson(res, 404, { error: "Not found" });
        } catch (error) {
          sendJson(res, 500, {
            error: error instanceof Error ? error.message : "History API error",
          });
        }
      });
    },
  };
}

function writeNdjson(res: import("http").ServerResponse, obj: unknown) {
  res.write(`${JSON.stringify(obj)}\n`);
}

function beginNdjson(res: import("http").ServerResponse) {
  if (res.headersSent) return;
  res.statusCode = 200;
  res.setHeader("Content-Type", "application/x-ndjson; charset=utf-8");
  res.setHeader("Cache-Control", "no-cache, no-transform");
  res.setHeader("X-Accel-Buffering", "no");
  res.setHeader("Connection", "keep-alive");
}

async function runExtractStreaming(
  res: import("http").ServerResponse,
  savePath: string,
  signal?: AbortSignal,
) {
  beginNdjson(res);
  try {
    const result = await extractFirstTeam(savePath, {
      signal,
      onProgress: (p) => {
        writeNdjson(res, { type: "progress", ...p, extract: "first-team" });
      },
    });
    if (signal?.aborted) {
      if (!res.writableEnded) res.end();
      return;
    }
    writeNdjson(res, {
      type: "progress",
      phase: "scout",
      message: "Scanning favoured-club relations…",
      pct: 96,
      extract: "favoured-club",
    });
    let favouredClub: Record<string, unknown> | null = null;
    try {
      const scout = await extractFavouredClubScouts(savePath, {
        signal,
        onProgress: (p) => {
          const pct =
            typeof p.pct === "number"
              ? Math.min(99, 96 + Math.floor(p.pct * 0.03))
              : undefined;
          writeNdjson(res, {
            type: "progress",
            ...p,
            pct,
            extract: "favoured-club",
          });
        },
      });
      favouredClub = {
        clubId: scout.clubId,
        clubName: scout.clubName,
        clubNameShort: scout.clubNameShort,
        affinity: scout.affinity,
        hitCount: scout.hitCount,
        anchoredCount: scout.anchoredCount,
        elapsedMs: scout.elapsedMs,
        players: scout.players,
        error: null,
      };
    } catch (scoutError) {
      if (signal?.aborted) {
        if (!res.writableEnded) res.end();
        return;
      }
      const raw =
        scoutError instanceof Error
          ? scoutError.message
          : "Favoured-club scan failed";
      // Career .fm zstd tails often raise "Error in input stream" / frame noise.
      // Never fail the Squad upload for that — keep an empty scout payload.
      const zstdNoise =
        /error in input stream|unknown frame descriptor|zstd decompress/i.test(
          raw,
        );
      favouredClub = {
        players: [],
        error: zstdNoise
          ? "Favoured-club scan could not finish reading this save (zstd tail). Re-upload or try again."
          : raw,
      };
      writeNdjson(res, {
        type: "progress",
        phase: "scout",
        message: zstdNoise
          ? "First Team ready — favoured-club scan incomplete"
          : `Favoured-club scan skipped: ${raw}`,
        pct: 99,
        extract: "favoured-club",
      });
    }
    writeNdjson(res, { type: "result", ...result, favouredClub });
    res.end();
    void extractRosterFaces(collectExtractFaceUids(result)).catch((err) => {
      console.warn(
        "[fmt faces] roster extract failed:",
        err instanceof Error ? err.message : err,
      );
    });
    void extractRosterLogos(collectExtractLogoIds(result)).catch((err) => {
      console.warn(
        "[fmt logos] roster extract failed:",
        err instanceof Error ? err.message : err,
      );
    });
  } catch (error) {
    if (signal?.aborted) {
      if (!res.writableEnded) res.end();
      return;
    }
    writeNdjson(res, {
      type: "error",
      error: error instanceof Error ? error.message : "Roster API error",
    });
    res.end();
  }
}

async function runIdentityStreaming(
  res: import("http").ServerResponse,
  savePath: string,
  signal?: AbortSignal,
) {
  beginNdjson(res);
  try {
    // Kept for callers that need meta-only. T108: + / roster POST uses list extract.
    const result = await extractManagedIdentity(savePath, {
      signal,
      onProgress: (p) => {
        writeNdjson(res, { type: "progress", ...p, extract: "identity" });
      },
    });
    if (signal?.aborted) {
      if (!res.writableEnded) res.end();
      return;
    }
    writeNdjson(res, { type: "result", ...result });
    res.end();
  } catch (error) {
    if (signal?.aborted) {
      if (!res.writableEnded) res.end();
      return;
    }
    writeNdjson(res, {
      type: "error",
      error: error instanceof Error ? error.message : "Roster API error",
    });
    res.end();
  }
}

async function runScoutStreaming(
  res: import("http").ServerResponse,
  savePath: string,
  signal?: AbortSignal,
) {
  beginNdjson(res);
  try {
    const result = await extractFavouredClubScouts(savePath, {
      signal,
      onProgress: (p) => {
        writeNdjson(res, { type: "progress", ...p });
      },
    });
    if (signal?.aborted) {
      if (!res.writableEnded) res.end();
      return;
    }
    writeNdjson(res, { type: "result", ...result });
    res.end();
  } catch (error) {
    if (signal?.aborted) {
      if (!res.writableEnded) res.end();
      return;
    }
    writeNdjson(res, {
      type: "error",
      error: error instanceof Error ? error.message : "Scout API error",
    });
    res.end();
  }
}

function safeUploadName(raw: string): string {
  return (
    path.basename(raw).replace(/[^\w.\- ()\u00C0-\u024F]/g, "_") || "upload.fm"
  );
}

async function receiveUploadToDisk(
  req: import("http").IncomingMessage,
  destPath: string,
  onBytes?: (received: number, total: number | null) => void,
): Promise<void> {
  const totalRaw = req.headers["content-length"];
  const total = totalRaw ? Number(totalRaw) : null;
  let received = 0;
  let lastNotify = 0;
  await new Promise<void>((resolve, reject) => {
    const out = fs.createWriteStream(destPath);
    req.on("data", (chunk: Buffer | string) => {
      const n = typeof chunk === "string" ? Buffer.byteLength(chunk) : chunk.length;
      received += n;
      if (onBytes && received - lastNotify >= 2 * 1024 * 1024) {
        lastNotify = received;
        onBytes(received, total && Number.isFinite(total) ? total : null);
      }
    });
    req.on("error", reject);
    out.on("error", reject);
    out.on("finish", resolve);
    req.pipe(out);
  });
  onBytes?.(received, total && Number.isFinite(total) ? total : null);
}

type SaveChangeEvent = {
  saveName: string;
  mtimeMs: number;
  size: number;
};

const saveChangeListeners = new Set<(event: SaveChangeEvent) => void>();
let saveWatchStarted = false;
/** Active FMT save basename — copy even when data/saves has no file yet. */
let selectedSaveName: string | null = null;
const ingestInFlight = new Map<string, Promise<SaveChangeEvent | null>>();
const runExtractExclusive = createExtractGate();

function notifySaveChanged(event: SaveChangeEvent): void {
  for (const listener of saveChangeListeners) {
    try {
      listener(event);
    } catch {
      // ignore listener errors
    }
  }
}

function setSelectedSaveName(saveName: string | null | undefined): void {
  if (!saveName) return;
  const base = path.basename(saveName);
  if (!base.toLowerCase().endsWith(".fm")) return;
  if (isFmBackupVersionName(base)) return;
  selectedSaveName = base;
}

async function ingestTrackedLiveSave(
  liveName: string,
): Promise<SaveChangeEvent | null> {
  const key = path.basename(liveName).toLowerCase();
  const existing = ingestInFlight.get(key);
  if (existing) return existing;
  const run = ingestTrackedLiveSaveBody(liveName).finally(() => {
    ingestInFlight.delete(key);
  });
  ingestInFlight.set(key, run);
  return run;
}

async function ingestTrackedLiveSaveBody(
  liveName: string,
): Promise<SaveChangeEvent | null> {
  if (!shouldCopyLiveFmSave(liveName, rootDir, selectedSaveName)) {
    return null;
  }
  const dest =
    resolveFmSaveByName(liveName, rootDir) ?? repoSaveDestPath(liveName, rootDir);
  if (!dest) return null;
  const livePath = path.join(resolveFmGamesDir(), path.basename(liveName));
  if (!fs.existsSync(livePath)) return null;
  try {
    const liveNow = fs.statSync(livePath);
    if (destCoversLiveSnapshot(dest, liveNow)) return null;
  } catch {
    return null;
  }
  const stable = await waitForFileStable(livePath);
  if (!stable) return null;
  if (destCoversLiveSnapshot(dest, stable)) return null;
  const copied = await copyLiveFmSaveToRepo(livePath, dest);
  return {
    saveName: path.basename(dest),
    mtimeMs: copied.mtimeMs,
    size: copied.size,
  };
}

function ensureSaveWatch(): void {
  if (saveWatchStarted) return;
  saveWatchStarted = true;
  const repoDir = resolveRepoSavesDir(rootDir);
  fs.mkdirSync(repoDir, { recursive: true });
  const gamesDir = resolveFmGamesDir();
  if (!fs.existsSync(gamesDir)) {
    console.info(
      `[fmt saves] SI games dir not found (copy-sync idle): ${gamesDir}`,
    );
    return;
  }
  console.info(
    `[fmt saves] watching ${gamesDir} — copy selected/tracked .fm into data/saves, then extract`,
  );
  const pending = new Map<string, ReturnType<typeof setTimeout>>();
  const settling = new Set<string>();
  fs.watch(gamesDir, (_event, filename) => {
    if (!filename || !String(filename).toLowerCase().endsWith(".fm")) return;
    const key = String(filename);
    if (!shouldCopyLiveFmSave(key, rootDir, selectedSaveName)) return;
    const prev = pending.get(key);
    if (prev) clearTimeout(prev);
    pending.set(
      key,
      setTimeout(() => {
        pending.delete(key);
        if (settling.has(key)) return;
        settling.add(key);
        void (async () => {
          try {
            const event = await ingestTrackedLiveSave(key);
            if (event) notifySaveChanged(event);
          } catch {
            // FM may still be writing — poll/SSE client will retry
          } finally {
            settling.delete(key);
          }
        })();
      }, SAVE_WATCH_DEBOUNCE_MS),
    );
  });
}

function rosterApiPlugin(): Plugin {
  return {
    name: "fmt-roster-api",
    configureServer(server) {
      killStaleExtractPid();
      // Long extracts must not be killed by idle sockets.
      server.httpServer?.setTimeout(0);
      server.middlewares.use(async (req, res, next) => {
        const rawUrl = req.url ?? "/";
        const url = rawUrl.split("?")[0] ?? "";
        const reqUrl = new URL(rawUrl, "http://127.0.0.1");
        const isRoster = url.startsWith("/api/roster");
        const isScout = url.startsWith("/api/scout");
        if (!isRoster && !isScout) {
          next();
          return;
        }

        try {
          if (req.method === "GET" && url === "/api/roster/save-stat") {
            const save = reqUrl.searchParams.get("save");
            if (!save) {
              sendJson(res, 400, { error: "Query ?save=filename.fm required" });
              return;
            }
            const stat = statFmSave(save, rootDir);
            if (!stat) {
              sendJson(res, 404, {
                error: `Save not found on disk: ${path.basename(save)}`,
              });
              return;
            }
            sendJson(res, 200, stat);
            return;
          }

          if (req.method === "POST" && url === "/api/roster/pull-live") {
            // T097: no Update-from-games / disk-linked recopy.
            sendJson(res, 410, {
              error: "Live games copy is disabled — add a save with +",
            });
            return;
          }

          if (req.method === "GET" && url === "/api/roster/events") {
            // T097: no SSE save-changed. Do not start SI games watch.
            sendJson(res, 410, { error: "Save-changed events are disabled" });
            return;
          }

          if (req.method === "POST" && url === "/api/roster/abort-extract") {
            killStaleExtractPid();
            sendJson(res, 200, { aborted: true });
            return;
          }

          if (req.method === "GET" && url === "/api/roster/first-team") {
            // T097: no disk GET extract. Identity is POST + only.
            sendJson(res, 405, {
              error: "Extract starts from + only — GET disk extract is disabled",
            });
            return;
          }

          if (req.method === "GET" && url === "/api/scout/favoured-club") {
            // T109: no disk GET extract from data/saves — working copy + delete only.
            sendJson(res, 405, {
              error:
                "Extract starts from + upload only — GET disk extract is disabled",
            });
            return;
          }

          if (
            req.method === "POST" &&
            (url === "/api/roster/first-team" ||
              url === "/api/scout/favoured-club")
          ) {
            const ct = String(req.headers["content-type"] || "").toLowerCase();
            // T109: + / Update lands in tmp/uploads working copy; delete after extract.
            const uploadDir = resolveWorkingUploadsDir(rootDir);
            fs.mkdirSync(uploadDir, { recursive: true });
            // T118: + / roster POST runs native club .dat Senior UniqueIDs → Squad
            // (unit `senior`; continue skips). Not +488 / extract-first-team-fast.
            // Identity-only helper remains for non-roster callers.
            const runStreaming =
              url === "/api/scout/favoured-club"
                ? runScoutStreaming
                : runExtractStreaming;

            if (
              ct.includes("application/octet-stream") ||
              ct.includes("application/x-fm-save") ||
              ct === "" ||
              ct === "application/octet-stream"
            ) {
              const headerName = String(
                req.headers["x-fmt-filename"] || "upload.fm",
              );
              let decoded = headerName;
              try {
                decoded = decodeURIComponent(headerName);
              } catch {
                // keep raw
              }
              const filename = safeUploadName(decoded);
              if (!filename.toLowerCase().endsWith(".fm")) {
                sendJson(res, 400, { error: "File must be a .fm career save" });
                return;
              }
              const savePath = path.join(
                uploadDir,
                `${Date.now()}-${filename}`,
              );
              beginNdjson(res);
              writeNdjson(res, {
                type: "progress",
                phase: "upload",
                message: `Receiving ${filename}…`,
                pct: 1,
              });
              try {
                await receiveUploadToDisk(req, savePath, (received, total) => {
                  const pct =
                    total && total > 0
                      ? Math.min(8, 1 + Math.floor((7 * received) / total))
                      : 3;
                  writeNdjson(res, {
                    type: "progress",
                    phase: "upload",
                    message: `Receiving ${filename}…`,
                    pct,
                    outBytes: received,
                  });
                });
                writeNdjson(res, {
                  type: "progress",
                  phase: "upload",
                  message: "Upload complete — starting extract",
                  pct: 9,
                });
                await runExtractExclusive(() => {
                  const ac = new AbortController();
                  req.on("close", () => ac.abort());
                  return runStreaming(res, savePath, ac.signal);
                });
              } finally {
                // T109: delete working .fm after success or abort/fail (best-effort).
                cleanupWorkingFm(savePath);
              }
              return;
            }

            sendJson(res, 400, {
              error:
                "Expected Content-Type application/octet-stream with X-Fmt-Filename",
            });
            return;
          }

          sendJson(res, 404, { error: "Not found" });
        } catch (error) {
          if (!res.headersSent) {
            sendJson(res, 500, {
              error:
                error instanceof Error ? error.message : "Roster API error",
            });
          } else {
            writeNdjson(res, {
              type: "error",
              error:
                error instanceof Error ? error.message : "Roster API error",
            });
            res.end();
          }
        }
      });
    },
  };
}

export default defineConfig({
  base: "./",
  root: "web",
  server: {
    port: 5173,
    open: true,
  },
  plugins: [
    historyApiPlugin(),
    rosterApiPlugin(),
    facesApiPlugin(),
    logosApiPlugin(),
  ],
  resolve: {
    alias: {
      "@shared": path.join(rootDir, "shared"),
    },
  },
});
