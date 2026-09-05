import { describe, expect, it } from "vitest";
import {
  APP_TONE_SUPER,
  FMT_ATTR_TONE_COLORS,
  toneClassName,
  toneCssVar,
  toneDefaultHex,
} from "./attr-colors";

describe("attr tone palette", () => {
  it("locks FMT design mid to R230 G230 B250", () => {
    expect(FMT_ATTR_TONE_COLORS.mid).toBe("#e6e6fa");
    expect(toneDefaultHex("mid")).toBe("#e6e6fa");
  });

  it("exposes Super neon above matte high green", () => {
    expect(FMT_ATTR_TONE_COLORS.super).toBe("#65e53a");
    expect(APP_TONE_SUPER).toBe("#65e53a");
    expect(FMT_ATTR_TONE_COLORS.high).toBe("#1b7a34");
    expect(toneCssVar("super")).toBe("--attr-tone-super");
    expect(toneClassName("super")).toBe("attr-tone-super");
    expect(toneCssVar("high")).toBe("--attr-tone-high");
    expect(toneClassName("upper")).toBe("attr-tone-upper");
  });
});
