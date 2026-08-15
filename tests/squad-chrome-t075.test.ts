import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const html = fs.readFileSync(
  path.join(process.cwd(), "web", "index.html"),
  "utf8",
);

describe("T075 four-tab chrome", () => {
  it("offers Squad, Loans, Mentoring, Progress in that order", () => {
    const tabs = [
      ...html.matchAll(
        /id="squad-view-(?:first-team|loans|mentoring|progress)"[\s\S]*?>\s*([^<]+)\s*</g,
      ),
    ].map((m) => m[1].trim());
    expect(tabs).toEqual(["Squad", "Loans", "Mentoring", "Progress"]);
  });

  it("has no Ranker / Best Personalities navigator entry", () => {
    expect(html).not.toMatch(/data-tool="rank"/);
    expect(html).not.toMatch(/>\s*Best Personalities\s*</);
  });

  it("keeps the Loans tab", () => {
    expect(html).toMatch(/id="squad-view-loans"/);
    expect(html).toMatch(/id="squad-loans-pane"/);
  });
});
