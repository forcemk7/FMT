import {
  FM_DATABASE_VERSIONS,
  FM_GAME_VERSIONS,
} from "./fm-meta.ts";

export type SaveMetaProbe = {
  gameVersion?: string;
  database?: string;
  /** How the values were obtained — useful while we learn the save format. */
  source: "strings" | "filename" | "none";
};

const PROBE_BYTES = 4 * 1024 * 1024;

/** Decode bytes as Latin-1 so every byte is searchable as a char. */
function asLatin1(bytes: Uint8Array): string {
  let out = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    out += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return out;
}

/**
 * FM 26.3.x clients still report database 26.2 in-game.
 * Use this when a game version is known but no DB string was found.
 */
export function impliedDatabaseForGameVersion(
  gameVersion: string,
): string | undefined {
  const match = gameVersion.match(/(\d+)\.(\d+)\.(\d+)\s*$/);
  if (!match) return undefined;
  const major = Number(match[1]);
  const minor = Number(match[2]);
  if (major !== 26) return undefined;
  if (minor >= 2) return "26.2.0";
  if (minor === 1) return "26.1.0";
  if (minor === 0) return "26.0.0";
  return undefined;
}

function findGameVersion(haystack: string): string | undefined {
  for (const version of FM_GAME_VERSIONS) {
    if (haystack.includes(version)) return version;
  }
  for (const version of FM_GAME_VERSIONS) {
    const patch = version.replace(/^FM26\s+/, "");
    if (haystack.includes(patch)) return version;
  }
  return undefined;
}

function findDatabase(
  haystack: string,
  gameVersion?: string,
): string | undefined {
  const gamePatch = gameVersion?.replace(/^FM26\s+/, "");
  for (const version of FM_DATABASE_VERSIONS) {
    if (!haystack.includes(version)) continue;
    if (gamePatch && version === gamePatch) {
      // Same digits as the game patch — only trust if it also appears
      // outside the "FM26 …" game-version label.
      const withoutGameLabel = haystack.split(`FM26 ${version}`).join("");
      if (!withoutGameLabel.includes(version)) continue;
    }
    return version;
  }
  return undefined;
}

export function probeText(text: string): Omit<SaveMetaProbe, "source"> {
  const gameVersion = findGameVersion(text);
  const database =
    findDatabase(text, gameVersion) ??
    (gameVersion ? impliedDatabaseForGameVersion(gameVersion) : undefined);
  return {
    ...(gameVersion ? { gameVersion } : {}),
    ...(database ? { database } : {}),
  };
}

export function probeBytes(bytes: Uint8Array): Omit<SaveMetaProbe, "source"> {
  return probeText(asLatin1(bytes));
}

/**
 * Best-effort metadata from a browsed save.
 * Today: Latin-1 string scan of the first few MB (+ filename fallback).
 * Container (FM26): 26-byte `fmf.` header, byte 25 = 3 (zstd), then a
 * zstd stream of nested `tad.` sections; the large `DB` tad holds game data.
 * Next: decompress + walk tad records before scanning / player import.
 */
export async function probeSaveFile(file: File): Promise<SaveMetaProbe> {
  const slice = file.slice(0, Math.min(file.size, PROBE_BYTES));
  const fromBytes = probeBytes(new Uint8Array(await slice.arrayBuffer()));
  if (fromBytes.gameVersion || fromBytes.database) {
    return { ...fromBytes, source: "strings" };
  }

  const fromName = probeText(file.name);
  if (fromName.gameVersion || fromName.database) {
    return { ...fromName, source: "filename" };
  }

  return { source: "none" };
}
