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

  it("exposes CSS var and class helpers for any app tone", () => {
    expect(toneCssVar("high")).toBe("--attr-tone-high");
    expect(toneCssVar("mid")).toBe("--attr-tone-mid");
    expect(toneCssVar("super")).toBe("--attr-tone-super");
    expect(toneClassName("upper")).toBe("attr-tone-upper");
    expect(toneClassName("super")).toBe("attr-tone-super");
    expect(toneDefaultHex("super")).toBe(APP_TONE_SUPER);
  });
});
