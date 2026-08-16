import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { saveFileMatchesSlot } from "../web/roster-store.ts";

const root = process.cwd();
const main = fs.readFileSync(path.join(root, "web", "main.ts"), "utf8");
const css = fs.readFileSync(path.join(root, "web", "styles.css"), "utf8");
const store = fs.readFileSync(path.join(root, "web", "roster-store.ts"), "utf8");
const py = fs.readFileSync(
  path.join(root, "scripts", "extract-managed-team.py"),
  "utf8",
);

describe("T101 save cards lock identity — FM24/FM26, continue date, update-same-name", () => {
  it("persists tagHex and maps 01→FM26 / 02→FM24", () => {
    expect(store).toMatch(/tagHex\?: string \| null/);
    expect(main).toMatch(/editionFromTagHex/);
    expect(main).toMatch(/hex === "00950e01"\) return "FM26"/);
    expect(main).toMatch(/hex === "00950e02"\) return "FM24"/);
    expect(main).toMatch(/roster-saves-item-edition/);
    expect(css).toMatch(/\.roster-saves-item-edition/);
    expect(css).toMatch(/width: 2\.7rem/);
    expect(py).toMatch(/"tagHex": identity\["tagHex"\]/);
  });

  it("cards show pill, club name, Uploaded, ID, Game Date, update+delete icons", () => {
    expect(main).toMatch(/Uploaded: \$\{escapeHtml\(uploaded\)\}/);
    expect(main).toMatch(/ID: \$\{escapeHtml\(\s*idText/);
    expect(main).toMatch(/Game Date: \$\{escapeHtml\(\s*inGame/);
    expect(main).toMatch(/hour12: true/);
    expect(main).toMatch(/dataset\.action = "update"/);
    expect(main).toMatch(/dataset\.action = "delete"/);
    expect(main).not.toMatch(/dataset\.action = "edit"/);
    expect(main).not.toMatch(/deleteBtn\.textContent = "Delete"/);
  });

  it("Update with a different .fm filename does not replace the slot", () => {
    expect(saveFileMatchesSlot("Career Save.fm", "Career Save.fm")).toBe(true);
    expect(saveFileMatchesSlot("career save.FM", "Career Save.fm")).toBe(true);
    expect(saveFileMatchesSlot("Other.fm", "Career Save.fm")).toBe(false);
    expect(main).toMatch(/saveFileMatchesSlot\(file\.name, rosterAmendTarget\)/);
    expect(main).toMatch(/use \+ for a different Career Save/);
    expect(main).toMatch(/T101: Update same filename only/);
  });

  it("menu is wider than T100 and auto-sync stays dead", () => {
    expect(css).toMatch(
      /min-width: min\(36rem, calc\(100vw - 1\.5rem\)\)/,
    );
    expect(css).toMatch(
      /max-width: min\(44rem, calc\(100vw - 1\.5rem\)\)/,
    );
    expect(css).not.toMatch(
      /min-width: min\(24rem, calc\(100vw - 1\.5rem\)\)/,
    );
    expect(main).toMatch(
      /T097: no poll, no SSE, no startup disk refresh, no Update-from-games/,
    );
  });
});
