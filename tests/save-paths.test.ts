import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  assertNotLiveFmGamesSave,
  copyLiveFmSaveToRepo,
  destCoversLiveSnapshot,
  isFmBackupVersionName,
  isLiveFmGamesSavePath,
  listFmSavePaths,
  repoSaveDestPath,
  resolveFmSaveByName,
  resolveRepoSavesDir,
  saveSearchDirs,
  shouldCopyLiveFmSave,
  statFmSave,
  waitForFileStable,
} from "../shared/save/save-paths.ts";
import { extractFirstTeam } from "../shared/save/extract-first-team.ts";

const tmpRoots: string[] = [];

function makeRoot(): string {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "fmt-save-paths-"));
  tmpRoots.push(root);
  fs.mkdirSync(resolveRepoSavesDir(root), { recursive: true });
  return root;
}

afterEach(() => {
  for (const root of tmpRoots.splice(0)) {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

describe("save-paths", () => {
  it("searches only data/saves — never Sports Interactive/games", () => {
    const root = makeRoot();
    expect(saveSearchDirs(root)).toEqual([resolveRepoSavesDir(root)]);
    expect(
      isLiveFmGamesSavePath(
        "C:\\Users\\x\\Documents\\Sports Interactive\\Football Manager 26\\games\\Career.fm",
      ),
    ).toBe(true);
    expect(
      isLiveFmGamesSavePath(path.join(resolveRepoSavesDir(root), "Career.fm")),
    ).toBe(false);
    expect(() =>
      assertNotLiveFmGamesSave(
        "/Users/x/Documents/Sports Interactive/Football Manager 26/games/Career.fm",
      ),
    ).toThrow(/data\/saves/);
  });

  it("finds saves in repo data/saves by exact and case-insensitive name", () => {
    const root = makeRoot();
    const savePath = path.join(resolveRepoSavesDir(root), "My Career.fm");
    fs.writeFileSync(savePath, "fake");

    expect(resolveFmSaveByName("My Career.fm", root)).toBe(savePath);
    expect(resolveFmSaveByName("my career.fm", root)).toBe(savePath);
    expect(statFmSave("My Career.fm", root)?.path).toBe(savePath);
  });

  it("lists .fm files under data/saves", () => {
    const root = makeRoot();
    const savesDir = resolveRepoSavesDir(root);
    const a = path.join(savesDir, "a.fm");
    const b = path.join(savesDir, "b.fm");
    fs.writeFileSync(a, "1");
    fs.writeFileSync(b, "2");
    fs.writeFileSync(path.join(savesDir, "notes.txt"), "n");

    const listed = listFmSavePaths(root)
      .map((p) => path.basename(p))
      .sort();
    expect(listed).toEqual(["a.fm", "b.fm"]);
  });

  it("returns null when save is missing", () => {
    const root = makeRoot();
    expect(resolveFmSaveByName("missing.fm", root)).toBeNull();
    expect(statFmSave("missing.fm", root)).toBeNull();
  });

  it("copies the selected Career Save when dest is missing; skips v02 and others", () => {
    const root = makeRoot();
    const selected = "FC Schalke 04 - Bastian König - FM24Career.fm";
    const dest = repoSaveDestPath(selected, root);
    expect(dest).toBe(path.join(resolveRepoSavesDir(root), selected));
    expect(resolveFmSaveByName(selected, root)).toBeNull();

    expect(isFmBackupVersionName(selected)).toBe(false);
    expect(
      isFmBackupVersionName(
        "FC Schalke 04 - Bastian König - FM24Career (v02).fm",
      ),
    ).toBe(true);
    expect(
      isFmBackupVersionName(
        "FC Schalke 04 - Bastian König - FM24Career (v10).fm",
      ),
    ).toBe(true);

    expect(shouldCopyLiveFmSave(selected, root, selected)).toBe(true);
    expect(shouldCopyLiveFmSave(selected, root, null)).toBe(false);
    expect(
      shouldCopyLiveFmSave(
        "FC Schalke 04 - Bastian König - FM24Career (v02).fm",
        root,
        selected,
      ),
    ).toBe(false);
    expect(shouldCopyLiveFmSave("Other Club.fm", root, selected)).toBe(false);

    fs.writeFileSync(dest!, "copy");
    expect(shouldCopyLiveFmSave(selected, root, null)).toBe(true);
    expect(
      shouldCopyLiveFmSave(
        "FC Schalke 04 - Bastian König - FM24Career (v02).fm",
        root,
        selected,
      ),
    ).toBe(false);
    expect(repoSaveDestPath("Career (v02).fm", root)).toBeNull();
  });

  it("skips recopy when dest already covers the live snapshot", () => {
    const root = makeRoot();
    const dest = path.join(resolveRepoSavesDir(root), "Career.fm");
    fs.writeFileSync(dest, "same-bytes");
    const destSt = fs.statSync(dest);
    expect(
      destCoversLiveSnapshot(dest, {
        mtimeMs: destSt.mtimeMs - 1000,
        size: destSt.size,
      }),
    ).toBe(true);
    expect(
      destCoversLiveSnapshot(dest, {
        mtimeMs: destSt.mtimeMs + 1000,
        size: destSt.size,
      }),
    ).toBe(false);
    expect(
      destCoversLiveSnapshot(dest, {
        mtimeMs: destSt.mtimeMs - 1000,
        size: destSt.size + 1,
      }),
    ).toBe(false);
    expect(
      destCoversLiveSnapshot(path.join(resolveRepoSavesDir(root), "missing.fm"), {
        mtimeMs: destSt.mtimeMs,
        size: destSt.size,
      }),
    ).toBe(false);
  });

  it("waitForFileStable resolves once size/mtime stop changing", async () => {
    const root = makeRoot();
    const filePath = path.join(resolveRepoSavesDir(root), "live.fm");
    fs.writeFileSync(filePath, "v1");

    let writes = 0;
    const writer = setInterval(() => {
      writes += 1;
      if (writes > 2) {
        clearInterval(writer);
        return;
      }
      fs.writeFileSync(filePath, `v${writes + 1}`);
    }, 200);

    const stable = await waitForFileStable(filePath, {
      pollMs: 100,
      stableMs: 350,
      maxMs: 5000,
    });
    clearInterval(writer);
    expect(stable).not.toBeNull();
    expect(stable!.size).toBe(fs.statSync(filePath).size);
  }, 10_000);

  it("waitForFileStable may stat a live games path (no extract assert)", async () => {
    const root = makeRoot();
    const liveDir = path.join(
      root,
      "Documents",
      "Sports Interactive",
      "Football Manager 26",
      "games",
    );
    fs.mkdirSync(liveDir, { recursive: true });
    const livePath = path.join(liveDir, "Career.fm");
    fs.writeFileSync(livePath, "v1");
    const stable = await waitForFileStable(livePath, {
      pollMs: 50,
      stableMs: 80,
      maxMs: 2000,
    });
    expect(stable).not.toBeNull();
    expect(stable!.size).toBe(2);
  });

  it("copyLiveFmSaveToRepo copies into data/saves and skips untracked names", async () => {
    const root = makeRoot();
    const liveDir = path.join(
      root,
      "Documents",
      "Sports Interactive",
      "Football Manager 26",
      "games",
    );
    fs.mkdirSync(liveDir, { recursive: true });
    const livePath = path.join(liveDir, "Career.fm");
    const otherLive = path.join(liveDir, "Other.fm");
    fs.writeFileSync(livePath, "tracked-bytes");
    fs.writeFileSync(otherLive, "untracked-bytes");
    const dest = path.join(resolveRepoSavesDir(root), "Career.fm");
    fs.writeFileSync(dest, "old");

    const copied = await copyLiveFmSaveToRepo(livePath, dest, {
      retries: 0,
      retryMs: 10,
    });
    expect(fs.readFileSync(dest, "utf8")).toBe("tracked-bytes");
    expect(copied.size).toBe("tracked-bytes".length);
    expect(resolveFmSaveByName("Other.fm", root)).toBeNull();

    await expect(
      copyLiveFmSaveToRepo(dest, dest, { retries: 0 }),
    ).rejects.toThrow(/source must be/);
    await expect(
      copyLiveFmSaveToRepo(livePath, livePath, { retries: 0 }),
    ).rejects.toThrow(/data\/saves/);
  });

  it("copyLiveFmSaveToRepo creates dest when data/saves has no file yet", async () => {
    const root = makeRoot();
    const liveDir = path.join(
      root,
      "Documents",
      "Sports Interactive",
      "Football Manager 26",
      "games",
    );
    fs.mkdirSync(liveDir, { recursive: true });
    const livePath = path.join(liveDir, "Career.fm");
    fs.writeFileSync(livePath, "first-copy");
    const dest = repoSaveDestPath("Career.fm", root);
    expect(dest).not.toBeNull();
    expect(fs.existsSync(dest!)).toBe(false);

    const copied = await copyLiveFmSaveToRepo(livePath, dest!, {
      retries: 0,
      retryMs: 10,
    });
    expect(fs.readFileSync(dest!, "utf8")).toBe("first-copy");
    expect(copied.size).toBe("first-copy".length);
    expect(resolveFmSaveByName("Career.fm", root)).toBe(dest);
  });

  it("extractFirstTeam refuses a live SI games path before opening it", async () => {
    await expect(
      extractFirstTeam(
        "C:\\Users\\x\\Documents\\Sports Interactive\\Football Manager 26\\games\\Career.fm",
      ),
    ).rejects.toThrow(/data\/saves/);
  });

  it("extractFirstTeam does not spawn when already aborted", async () => {
    const dummy = path.join(os.tmpdir(), `fmt-abort-${Date.now()}.fm`);
    fs.writeFileSync(dummy, "not-a-save");
    try {
      const ac = new AbortController();
      ac.abort();
      await expect(
        extractFirstTeam(dummy, { signal: ac.signal }),
      ).rejects.toThrow(/Extract aborted/);
    } finally {
      fs.unlinkSync(dummy);
    }
  });
});
