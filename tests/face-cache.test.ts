import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  collectExtractFaceUids,
  copyFaceIntoRepo,
  findCachedFace,
  resolveRepoFacesDir,
} from "../shared/faces/face-cache.ts";
import type { FirstTeamExtract } from "../shared/save/types.ts";

const tmpRoots: string[] = [];
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);

function makeRoot(): string {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "fmt-face-cache-"));
  tmpRoots.push(root);
  return root;
}

afterEach(() => {
  for (const root of tmpRoots.splice(0)) {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

describe("face cache", () => {
  it("copies a pack file into data/faces/{uid}.png and skips a second copy", () => {
    const root = makeRoot();
    const facesDir = resolveRepoFacesDir(root);
    const src = path.join(root, "src-kizza.png");
    fs.writeFileSync(src, PNG);

    const dest = copyFaceIntoRepo(src, facesDir, 2002185604);
    expect(dest).toBe(path.join(facesDir, "2002185604.png"));
    expect(findCachedFace(facesDir, 2002185604)).toBe(dest);
    expect(fs.readFileSync(dest).equals(PNG)).toBe(true);

    fs.writeFileSync(src, Buffer.from("nope"));
    const again = copyFaceIntoRepo(src, facesDir, 2002185604);
    expect(again).toBe(dest);
    expect(fs.readFileSync(dest).equals(PNG)).toBe(true);
  });

  it("collects FT + II + U19 uids and ignores junk", () => {
    const extract = {
      players: [{ uid: 2000175080 }, { uid: 0 }],
      reserves: { players: [{ uid: 2002400248 }] },
      u19: { players: [{ uid: 2002185604 }] },
    } as FirstTeamExtract;
    expect(collectExtractFaceUids(extract).sort((a, b) => a - b)).toEqual([
      2000175080, 2002185604, 2002400248,
    ]);
    expect(findCachedFace(resolveRepoFacesDir(makeRoot()), 1)).toBeNull();
  });
});
