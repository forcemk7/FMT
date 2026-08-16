import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const main = fs.readFileSync(path.join(root, "web", "main.ts"), "utf8");

describe("T102 structured hover tooltip on save cards", () => {
  it("syncRosterSavesMenu title is the six-line labeled list", () => {
    expect(main).toMatch(/function saveCardHoverTitle\(/);
    expect(main).toMatch(/function syncRosterSavesMenu\(/);
    expect(main).toMatch(/`Game Version: \$\{parts\.edition \?\? "—"\}`/);
    expect(main).toMatch(/`Club Name: \$\{parts\.clubName\}`/);
    expect(main).toMatch(/`Club ID: \$\{parts\.clubId\}`/);
    expect(main).toMatch(/`Game Date: \$\{parts\.gameDate\}`/);
    expect(main).toMatch(/`Uploaded: \$\{parts\.uploaded\}`/);
    expect(main).toMatch(/row\.title = hoverTitle/);
    expect(main).toMatch(/selectBtn\.title = hoverTitle/);
    expect(main).toMatch(/gameDate: inGame/);
    expect(main).toMatch(/formatInGameDateRow\(entry\.gameDate\)/);
    expect(main).toMatch(/formatUploadedAtRow\(entry\.extractedAt\)/);
    expect(main).not.toMatch(/`Uploaded \$\{uploaded\}`/);
    expect(main).not.toMatch(/`Game Date \$\{formatInGameDate\(entry\.gameDate\)\}`/);
  });
});
