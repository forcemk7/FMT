import { describe, expect, it } from "vitest";
import {
  impliedDatabaseForGameVersion,
  probeBytes,
  probeText,
} from "../web/save-meta.ts";

describe("save-meta probe", () => {
  it("maps 26.3.x game clients to database 26.2.0", () => {
    expect(impliedDatabaseForGameVersion("FM26 26.3.2")).toBe("26.2.0");
    expect(impliedDatabaseForGameVersion("FM26 26.1.3")).toBe("26.1.0");
  });

  it("finds catalog strings in a synthetic save blob", () => {
    const text = "noise FM26 26.3.2 more noise database=26.2.0 end";
    const bytes = Uint8Array.from(text, (c) => c.charCodeAt(0));
    expect(probeBytes(bytes)).toEqual({
      gameVersion: "FM26 26.3.2",
      database: "26.2.0",
    });
  });

  it("implies database when only the game version is present", () => {
    expect(probeText("build FM26 26.3.0")).toEqual({
      gameVersion: "FM26 26.3.0",
      database: "26.2.0",
    });
  });
});
