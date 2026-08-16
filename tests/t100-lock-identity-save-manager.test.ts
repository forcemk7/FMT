import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const main = fs.readFileSync(path.join(root, "web", "main.ts"), "utf8");
const css = fs.readFileSync(path.join(root, "web", "styles.css"), "utf8");
const store = fs.readFileSync(path.join(root, "web", "roster-store.ts"), "utf8");

describe("T100 lock identity upload; last + is Active; compact cards", () => {
  it("new + / Edit persist sets Active to that save", () => {
    expect(store).toMatch(/options\?: \{ setActive\?: boolean \}/);
    expect(store).toMatch(/pinThisSave = options\?\.setActive === true/);
    expect(store).toMatch(/keepActive/);
    expect(main).toMatch(/\{ setActive: true \}/);
    expect(main).toMatch(/T100: \+ \/ Edit persist makes this save Active/);
  });

  it("cards are two rows: club+id | uploaded; game date | edit+delete icons", () => {
    expect(main).toMatch(/formatUploadedAtRow\(entry\.extractedAt\)/);
    expect(main).toMatch(/roster-saves-item-uploaded/);
    expect(main).toMatch(/formatInGameDateRow\(entry\.gameDate\)/);
    expect(main).toMatch(/dataset\.action = "update"/);
    expect(main).toMatch(/dataset\.action = "delete"/);
    expect(main).not.toMatch(/deleteBtn\.textContent = "Delete"/);
    expect(main).not.toMatch(/roster-saves-row-btn is-danger/);
    expect(css).toMatch(/\.roster-saves-item-uploaded/);
    expect(css).toMatch(/\.roster-saves-row-icon/);
    expect(css).toMatch(
      /\.roster-saves-row \{\s*display: grid;\s*grid-template-columns: minmax\(0, 1fr\) auto;\s*grid-template-rows: auto auto;/,
    );
  });

  it("Edit opens the identity file picker into that slot; auto-sync stays dead", () => {
    expect(main).toMatch(/action === "update"/);
    expect(main).toMatch(/rosterAmendTarget = name;/);
    expect(main).toMatch(/openRosterFilePicker\(\)/);
    expect(main).toMatch(
      /T097: no poll, no SSE, no startup disk refresh, no Update-from-games/,
    );
    expect(main).not.toMatch(/dataset\.action = "edit"/);
  });
});
