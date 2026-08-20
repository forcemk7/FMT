import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { SQUAD_HA_UNIT_ORDER } from "../web/squad-ha-table.ts";

const root = process.cwd();
const extractPy = fs.readFileSync(
  path.join(root, "scripts", "extract-squad-lists.py"),
  "utf8",
);

describe("T114 +488 namelist — superseded by T118", () => {
  it("extract no longer ships +488 as mentoring pool", () => {
    expect(extractPy).toMatch(/native-club-dat-senior-v1/);
    expect(extractPy).not.toMatch(/native-clubid-plus488-v1/);
    expect(extractPy).not.toMatch(/CLUB_ID_NAMELIST_REL = 488/);
    expect(SQUAD_HA_UNIT_ORDER).toContain("senior");
    expect(SQUAD_HA_UNIT_ORDER).toContain("list");
  });
});
