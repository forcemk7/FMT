import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const extractPy = fs.readFileSync(
  path.join(root, "scripts", "extract-squad-lists.py"),
  "utf8",
);

describe("T111 Senior object path — superseded by T118", () => {
  it("extract uses club .dat Senior UniqueIDs (not T111 object path)", () => {
    expect(extractPy).toMatch(/native-club-dat-senior-v1/);
    expect(extractPy).not.toMatch(/senior-squad-object-v1/);
    expect(extractPy).not.toMatch(/native-clubid-plus488-v1/);
  });
});
