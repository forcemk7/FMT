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
  buildLogoIndex,
  buildLogoIndexStub,
  resolveLogoPath,
  type LogoIndex,
} from "./shared/logos/logo-index.ts";
import {
  emptyHistoryStore,
  normalizeHistoryStore,
  playerCount,
  type HistoryStore,
} from "./shared/history-store.ts";
import {
  extractFirstTeam,
  resolveDefaultSavePath,
} from "./shared/save/extract-first-team.ts";
import { extractFavouredClubScouts } from "./shared/save/extract-favoured-scouts.ts";
import {
  resolveFmGamesDir,
  resolveFmSaveByName,
  SAVE_WATCH_DEBOUNCE_MS,
  statFmSave,
  waitForFileStable,
} from "./shared/save/save-paths.ts";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)));
const historyPath = path.join(rootDir, "data", "history.json");
const historyBakPath = path.join(rootDir, "data", "history.json.bak");

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
      void ensureLogoIndex().catch((err) => {
        console.warn(
          "[fmt logos] index failed:",
          err instanceof Error ? err.message : err,
        );
      });

      server.middlewares.use(async (req, res, next) => {
        const url = req.url?.split("?")[0] ?? "";
        if (!url.startsWith("/api/logos")) {
          next();
          return;
        }

        try {
          if (req.method === "GET" && url === "/api/logos/status") {
            try {
              const idx = await ensureLogoIndex();
              sendJson(res, 200, {
                graphicsRoot: idx.graphicsRoot,
                packRoot: idx.packRoot,
                mapped: idx.byClubId.size,
                clubDirs: idx.clubDirs.length,
                configCount: idx.configCount,
                ready: true,
              });
            } catch (error) {
              sendJson(res, 200, {
                graphicsRoot: resolveDefaultGraphicsRoot(),
                mapped: 0,
                clubDirs: 0,
                configCount: 0,
                ready: false,
                error:
                  error instanceof Error ? error.message : "Logo index failed",
              });
            }
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
            let filePath = resolveLogoPathForRequest(clubId);
            if (!filePath) {
              const idx = await ensureLogoIndex();
              filePath = resolveLogoPath(idx, clubId);
            } else {
              void ensureLogoIndex();
            }
            if (!filePath || !fs.existsSync(filePath)) {
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
      void ensureFaceIndex().catch((err) => {
        console.warn(
          "[fmt faces] index failed:",
          err instanceof Error ? err.message : err,
        );
      });

      server.middlewares.use(async (req, res, next) => {
        const url = req.url?.split("?")[0] ?? "";
        if (!url.startsWith("/api/faces")) {
          next();
          return;
        }

        try {
          if (req.method === "GET" && url === "/api/faces/status") {
            try {
              const idx = await ensureFaceIndex();
              sendJson(res, 200, {
                graphicsRoot: idx.graphicsRoot,
                mapped: idx.byUid.size,
                faceDirs: idx.faceDirs.length,
                configCount: idx.configCount,
                ready: true,
              });
            } catch (error) {
              sendJson(res, 200, {
                graphicsRoot: resolveDefaultGraphicsRoot(),
                mapped: 0,
                faceDirs: 0,
                configCount: 0,
                ready: false,
                error:
                  error instanceof Error ? error.message : "Face index failed",
              });
            }
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
            let filePath = resolveFacePathForRequest(uid);
            // Regen faces need the full index; wait only when cutout missed.
            if (!filePath) {
              const idx = await ensureFaceIndex();
              filePath = resolveFacePath(idx, uid);
            } else {
              // Kick off full index in background if not ready yet.
              void ensureFaceIndex();
            }
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
) {
  beginNdjson(res);
  try {
    const result = await extractFirstTeam(savePath, {
      onProgress: (p) => {
        writeNdjson(res, { type: "progress", ...p, extract: "first-team" });
      },
    });
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
  } catch (error) {
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
) {
  beginNdjson(res);
  try {
    const result = await extractFavouredClubScouts(savePath, {
      onProgress: (p) => {
        writeNdjson(res, { type: "progress", ...p });
      },
    });
    writeNdjson(res, { type: "result", ...result });
    res.end();
  } catch (error) {
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

function notifySaveChanged(event: SaveChangeEvent): void {
  for (const listener of saveChangeListeners) {
    try {
      listener(event);
    } catch {
      // ignore listener errors
    }
  }
}

function ensureSaveWatch(): void {
  if (saveWatchStarted) return;
  saveWatchStarted = true;
  const dir = resolveFmGamesDir();
  if (!fs.existsSync(dir)) {
    console.info(`[fmt saves] FM games dir not found (auto-sync idle): ${dir}`);
    return;
  }
  console.info(`[fmt saves] watching ${dir} for .fm changes`);
  const pending = new Map<string, ReturnType<typeof setTimeout>>();
  const settling = new Set<string>();
  fs.watch(dir, (_event, filename) => {
    if (!filename || !String(filename).toLowerCase().endsWith(".fm")) return;
    const key = String(filename);
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
            const full = path.join(dir, key);
            const stable = await waitForFileStable(full);
            if (!stable) return;
            notifySaveChanged({
              saveName: key,
              mtimeMs: stable.mtimeMs,
              size: stable.size,
            });
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

          if (req.method === "GET" && url === "/api/roster/events") {
            ensureSaveWatch();
            res.writeHead(200, {
              "Content-Type": "text/event-stream; charset=utf-8",
              "Cache-Control": "no-cache, no-transform",
              Connection: "keep-alive",
            });
            res.write(": connected\n\n");
            const listener = (event: SaveChangeEvent) => {
              res.write(
                `data: ${JSON.stringify({ type: "save-changed", ...event })}\n\n`,
              );
            };
            saveChangeListeners.add(listener);
            req.on("close", () => {
              saveChangeListeners.delete(listener);
            });
            return;
          }

          if (req.method === "GET" && url === "/api/roster/first-team") {
            const saveQuery = reqUrl.searchParams.get("save");
            let savePath: string;
            if (saveQuery) {
              const resolved = resolveFmSaveByName(saveQuery, rootDir);
              if (!resolved) {
                sendJson(res, 404, {
                  error: `Save not found on disk: ${path.basename(saveQuery)}`,
                });
                return;
              }
              savePath = resolved;
            } else {
              savePath = resolveDefaultSavePath(rootDir);
            }
            await runExtractStreaming(res, savePath);
            return;
          }

          if (req.method === "GET" && url === "/api/scout/favoured-club") {
            const savePath = resolveDefaultSavePath(rootDir);
            await runScoutStreaming(res, savePath);
            return;
          }

          if (
            req.method === "POST" &&
            (url === "/api/roster/first-team" ||
              url === "/api/scout/favoured-club")
          ) {
            const ct = String(req.headers["content-type"] || "").toLowerCase();
            const uploadDir = path.join(rootDir, "tmp", "uploads");
            fs.mkdirSync(uploadDir, { recursive: true });
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
                await runStreaming(res, savePath);
              } finally {
                try {
                  fs.unlinkSync(savePath);
                } catch {
                  // ignore
                }
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
