import { describe, expect, it } from "vitest";
import {
  abilityToneFromScore,
  attributeDeltaTone,
  attributeTone,
  attributeZ,
} from "./attribute-tone";

describe("attributeTone (SD experiment)", () => {
  it("bands by z vs N(10,3)", () => {
    expect(attributeZ(19)).toBeCloseTo(3, 5);
    expect(attributeZ(16)).toBeCloseTo(2, 5);
    expect(attributeZ(13)).toBeCloseTo(1, 5);
    expect(attributeZ(7)).toBeCloseTo(-1, 5);

    expect(attributeTone("Passing", 20)).toBe("super");
    expect(attributeTone("Passing", 19)).toBe("super");
    expect(attributeTone("Passing", 18)).toBe("high");
    expect(attributeTone("Passing", 16)).toBe("high");
    expect(attributeTone("Technique", 15)).toBe("upper");
    expect(attributeTone("Technique", 13)).toBe("upper");
    expect(attributeTone("Crossing", 12)).toBe("mid");
    expect(attributeTone("Crossing", 8)).toBe("mid");
    expect(attributeTone("Crossing", 7)).toBe("low");
    expect(attributeTone("Crossing", 1)).toBe("low");
  });

  it("mirrors Controversy / Injury Proneness — Super only at 1–2", () => {
    expect(attributeTone("Controversy", 1)).toBe("super");
    expect(attributeTone("Controversy", 2)).toBe("super");
    expect(attributeTone("Controversy", 3)).toBe("high");
    expect(attributeTone("Controversy", 5)).toBe("high");
    expect(attributeTone("Controversy", 6)).toBe("upper");
    expect(attributeTone("Controversy", 8)).toBe("upper");
    expect(attributeTone("Controversy", 9)).toBe("mid");
    expect(attributeTone("Controversy", 13)).toBe("mid");
    expect(attributeTone("Controversy", 14)).toBe("low");
    expect(attributeTone("Controversy", 20)).toBe("low");
    expect(attributeTone("Injury Proneness", 2)).toBe("super");
    expect(attributeTone("Injury Proneness", 18)).toBe("low");
  });

  it("maps CA/PA via tenths with continuous SD bands", () => {
    expect(abilityToneFromScore(200)).toBe("super");
    expect(abilityToneFromScore(190)).toBe("super");
    expect(abilityToneFromScore(189)).toBe("high");
    expect(abilityToneFromScore(160)).toBe("high");
    expect(abilityToneFromScore(159)).toBe("upper");
    expect(abilityToneFromScore(130)).toBe("upper");
    expect(abilityToneFromScore(129)).toBe("mid");
    expect(abilityToneFromScore(80)).toBe("mid");
    expect(abilityToneFromScore(70)).toBe("low");
    expect(abilityToneFromScore(69)).toBe("low");
  });
});

describe("attributeDeltaTone", () => {
  it("uses green for gains and red for drops on standard attrs", () => {
    expect(attributeDeltaTone("Passing", 1)).toBe("high");
    expect(attributeDeltaTone("CA", -1)).toBe("low");
    expect(attributeDeltaTone("Pace", 0)).toBeNull();
  });

  it("inverts Controversy and Injury Proneness", () => {
    expect(attributeDeltaTone("Controversy", -1)).toBe("high");
    expect(attributeDeltaTone("Controversy", 1)).toBe("low");
    expect(attributeDeltaTone("Injury Proneness", -2)).toBe("high");
    expect(attributeDeltaTone("Injury Proneness", 1)).toBe("low");
  });
});
