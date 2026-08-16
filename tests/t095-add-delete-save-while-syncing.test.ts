import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const main = fs.readFileSync(path.join(root, "web", "main.ts"), "utf8");
const css = fs.readFileSync(path.join(root, "web", "styles.css"), "utf8");
const vite = fs.readFileSync(path.join(root, "vite.config.ts"), "utf8");

describe("T095 add or delete a save while another extract runs", () => {
  it("does not disable + while an extract is running", () => {
    expect(main).toMatch(
      /T095: \+ stays usable while A is extracting\. File picker opens\./,
    );
    expect(main).not.toMatch(/rosterUploadBtnEl\.disabled\s*=/);
    expect(main).not.toMatch(/rosterUploadEl\.disabled\s*=/);
    expect(css).toMatch(
      /\.squad-save-controller\.is-busy > :is\(button:not\(#roster-upload-btn\), \.roster-saves-wrap\)/,
    );
  });

  it("keeps Delete enabled on the Syncing row and aborts that Python", () => {
    expect(main).toMatch(/deleteBtn\.disabled = false;/);
    expect(main).not.toMatch(/deleteBtn\.disabled = isSyncing/);
    expect(main).toMatch(
      /T095: Delete on the Syncing row aborts that Python then removes the slot/,
    );
    expect(main).toMatch(
      /if \(name === rosterSyncingSaveName\) abortRosterExtract\(\)/,
    );
    expect(main).toMatch(/\/api\/roster\/abort-extract/);
    expect(vite).toMatch(/\/api\/roster\/abort-extract/);
    expect(vite).toMatch(/killStaleExtractPid\(\)/);
  });

  it("queues a chosen + upload ahead of König auto-sync", () => {
    expect(main).toMatch(/rosterManualExtractQueued/);
    expect(main).toMatch(/T097: no poll, no SSE, no startup disk refresh/);
  });
});
