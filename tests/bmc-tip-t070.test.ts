import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const html = fs.readFileSync(
  path.join(process.cwd(), "web", "index.html"),
  "utf8",
);

const BMC_URL = "https://buymeacoffee.com/mrramirez";

describe("T070 Buy Me a Coffee tip", () => {
  it("puts a real BMC link in shared header chrome", () => {
    const header = html.match(
      /<header class="app-header">[\s\S]*?<\/header>/,
    )?.[0];
    expect(header).toBeTruthy();
    expect(header).toContain(`href="${BMC_URL}"`);
    expect(header).toMatch(/target="_blank"/);
    expect(header).toMatch(/Buy me a coffee/);
    expect(header).toMatch(/optional thank-you/i);
  });

  it("does not gate the table behind payment", () => {
    expect(html).not.toMatch(/stripe/i);
    expect(html).not.toMatch(/paywall/i);
    expect(html).toMatch(/id="roster-body"/);
    expect(html).toMatch(/id="mentoring-add-btn"/);
  });
});
