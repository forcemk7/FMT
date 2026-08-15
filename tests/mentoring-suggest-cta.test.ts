import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const html = fs.readFileSync(
  path.join(process.cwd(), "web", "index.html"),
  "utf8",
);

describe("T071 Mentoring Suggest CTA", () => {
  it("has no Suggest button on Mentoring or the Add group picker", () => {
    expect(html).not.toMatch(/id="mentoring-suggest-btn"/);
    expect(html).not.toMatch(/id="mentoring-picker-suggest"/);
    expect(html).not.toMatch(/>\s*Suggest\s*</);
  });

  it("keeps Add group", () => {
    expect(html).toMatch(/id="mentoring-add-btn"/);
    expect(html).toMatch(/>\s*Add group\s*</);
  });
});
