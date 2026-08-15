import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  collectExtractLogoIds,
  copyLogoIntoRepo,
  countCachedImages,
  findCachedLogo,
  resolveRepoLogosDir,
} from "../shared/logos/logo-cache.ts";
import type { FirstTeamExtract } from "../shared/save/types.ts";

const tmpRoots: string[] = [];
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);

function makeRoot(): string {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "fmt-logo-cache-"));
  tmpRoots.push(root);
  return root;
}

afterEach(() => {
  for (const root of tmpRoots.splice(0)) {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

describe("logo cache", () => {
  it("copies a pack file into data/logos/{clubId}.png and skips a second copy", () => {
    const root = makeRoot();
    const logosDir = resolveRepoLogosDir(root);
    const src = path.join(root, "src-schalke.png");
    fs.writeFileSync(src, PNG);

    const dest = copyLogoIntoRepo(src, logosDir, 920);
    expect(dest).toBe(path.join(logosDir, "920.png"));
    expect(findCachedLogo(logosDir, 920)).toBe(dest);
    expect(countCachedImages(logosDir)).toBe(1);

    fs.writeFileSync(src, Buffer.from("nope"));
    expect(copyLogoIntoRepo(src, logosDir, 920)).toBe(dest);
    expect(fs.readFileSync(dest).equals(PNG)).toBe(true);
  });

  it("collects club + loan club ids", () => {
    const extract = {
      clubId: 920,
      reserves: {
        clubId: 921,
        players: [{ loan: { loanClubId: 3609393 } }],
      },
      players: [{ loan: { parentClubId: 50, loanClubId: null } }],
      u19: { players: [] },
    } as FirstTeamExtract;
    expect(collectExtractLogoIds(extract).sort((a, b) => a - b)).toEqual([
      50, 920, 921, 3609393,
    ]);
  });
});
