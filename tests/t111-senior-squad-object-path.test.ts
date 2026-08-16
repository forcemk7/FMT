import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const extractPy = fs.readFileSync(
  path.join(root, "scripts", "extract-squad-lists.py"),
  "utf8",
);

describe("T111 Senior object path — superseded by T114", () => {
  it("extract no longer claims senior-squad-object-v1", () => {
    expect(extractPy).toMatch(/native-clubid-plus488-v1/);
    expect(extractPy).not.toMatch(/senior-squad-object-v1/);
  });
});
