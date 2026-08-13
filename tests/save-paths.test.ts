import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  listFmSavePaths,
  resolveFmSaveByName,
  resolveRepoSavesDir,
  statFmSave,
  waitForFileStable,
} from "../shared/save/save-paths.ts";

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
      .filter((p) => p.startsWith(savesDir))
      .map((p) => path.basename(p))
      .sort();
    expect(listed).toEqual(["a.fm", "b.fm"]);
  });

  it("returns null when save is missing", () => {
    const root = makeRoot();
    expect(resolveFmSaveByName("missing.fm", root)).toBeNull();
    expect(statFmSave("missing.fm", root)).toBeNull();
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
});
