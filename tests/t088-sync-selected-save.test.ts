import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const main = fs.readFileSync(path.join(root, "web", "main.ts"), "utf8");
const css = fs.readFileSync(path.join(root, "web", "styles.css"), "utf8");
const store = fs.readFileSync(path.join(root, "web", "roster-store.ts"), "utf8");

describe("T088 sync belongs to the selected save", () => {
  it("does not always set Active to the upserted save", () => {
    expect(store).toMatch(/keepActive/);
    expect(store).not.toMatch(/activeSaveName:\s*entry\.saveName/);
  });

  it("starts disk extract only for the Active save", () => {
    expect(main).toMatch(
      /if \(saveName !== rosterStore\.activeSaveName\) return false;/,
    );
  });

  it("re-checks Active before a queued background extract", () => {
    expect(main).toMatch(/rosterBackgroundSyncQueued/);
    expect(main).toMatch(
      /Re-check Active — do not start B if the user is still on A, or A if they moved/,
    );
    expect(main).toMatch(
      /Re-check Active after the async pull — do not start a now-unselected save/,
    );
  });

  it("shows Syncing on the extracting save row, not the header controller", () => {
    expect(css).toMatch(/\.roster-saves-row\.is-syncing/);
    expect(main).toMatch(/rosterSyncingSaveName/);
    expect(main).toMatch(/roster-saves-item-badge is-syncing/);
    expect(main).toMatch(/rosterSaveControllerEl\.classList\.remove\("is-syncing"\)/);
  });
});
