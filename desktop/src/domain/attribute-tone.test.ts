import { describe, expect, it } from "vitest";
import { abilityToneFromScore, attributeTone } from "./attribute-tone";

describe("attributeTone", () => {
  it("uses FM four-band ranges for standard attrs", () => {
    expect(attributeTone("Passing", 16)).toBe("high");
    expect(attributeTone("Passing", 20)).toBe("high");
    expect(attributeTone("Technique", 15)).toBe("upper");
    expect(attributeTone("Technique", 11)).toBe("upper");
    expect(attributeTone("Crossing", 10)).toBe("mid");
    expect(attributeTone("Crossing", 6)).toBe("mid");
    expect(attributeTone("Crossing", 5)).toBe("low");
    expect(attributeTone("Crossing", 1)).toBe("low");
  });

  it("colors Important Matches like any standard attr", () => {
    expect(attributeTone("Important Matches", 16)).toBe("high");
    expect(attributeTone("Important Matches", 10)).toBe("mid");
    expect(attributeTone("Important Matches", 4)).toBe("low");
  });

  it("mirrors bands for Controversy and Injury Proneness", () => {
    expect(attributeTone("Controversy", 3)).toBe("high");
    expect(attributeTone("Controversy", 7)).toBe("upper");
    expect(attributeTone("Controversy", 12)).toBe("mid");
    expect(attributeTone("Controversy", 16)).toBe("low");
    expect(attributeTone("Injury Proneness", 2)).toBe("high");
    expect(attributeTone("Injury Proneness", 18)).toBe("low");
  });

  it("maps CA/PA via tenths", () => {
    expect(abilityToneFromScore(160)).toBe("high");
    expect(abilityToneFromScore(159)).toBe("upper");
    expect(abilityToneFromScore(110)).toBe("upper");
    expect(abilityToneFromScore(109)).toBe("mid");
    expect(abilityToneFromScore(60)).toBe("mid");
    expect(abilityToneFromScore(59)).toBe("low");
  });
});
