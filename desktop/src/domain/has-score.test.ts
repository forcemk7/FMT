import { describe, expect, it } from "vitest";
import type { LivePlayer } from "./adapters";
import {
  diminishingPersonalityValue,
  hasBand,
  hasProgress,
  HAS_PRACTICAL_CEILING,
  HAS_PRACTICAL_FLOOR,
  HAS_SCORE_CEILING,
  liveHasScore,
} from "./has-score";
import { abilityProgress, abilityToneFromScore } from "./attribute-tone";

function player(partial: Partial<LivePlayer>): LivePlayer {
  return {
    id: "1",
    name: "Test",
    age: 20,
    nationality: null,
    positions: ["MC"],
    bestRole: null,
    currentAbility: null,
    potentialAbility: null,
    form: null,
    averageRating: null,
    minutesPlayed: null,
    goals: null,
    assists: null,
    contractStatus: null,
    value: null,
    wage: null,
    squadImportance: null,
    developmentTrend: null,
    tacticalFit: null,
    roleFit: null,
    strengths: [],
    weaknesses: [],
    clubId: "1",
    transferInterest: null,
    loanInterest: null,
    transferAvailable: null,
    loanAvailable: null,
    ...partial,
  };
}

const personalityBase = {
  Professionalism: 12,
  Pressure: 12,
  Ambition: 12,
  Temperament: 12,
  Loyalty: 12,
  Sportsmanship: 12,
  Controversy: 10,
};

describe("diminishingPersonalityValue", () => {
  it("is linear up to the knee then tails off", () => {
    expect(diminishingPersonalityValue(8)).toBe(8);
    expect(diminishingPersonalityValue(10)).toBe(10);
    expect(diminishingPersonalityValue(14)).toBe(11);
    expect(diminishingPersonalityValue(20)).toBe(12.5);
  });
});

describe("liveHasScore", () => {
  it("prefers high professionalism over very high determination", () => {
    const proHeavy = liveHasScore(
      player({
        personalityAttributes: { ...personalityBase, Professionalism: 17, Pressure: 18 },
        attributes: { Determination: 14, Leadership: 16 },
      }),
    );
    const detHeavy = liveHasScore(
      player({
        personalityAttributes: { ...personalityBase, Professionalism: 12, Pressure: 12 },
        attributes: { Determination: 20, Leadership: 16 },
      }),
    );
    expect(proHeavy).not.toBeNull();
    expect(detHeavy).not.toBeNull();
    expect(proHeavy!).toBeGreaterThan(detHeavy!);
  });

  it("hits theoretical ceiling with all 20s and Controversy 1", () => {
    const score = liveHasScore(
      player({
        personalityAttributes: {
          Professionalism: 20,
          Pressure: 20,
          Ambition: 20,
          Temperament: 20,
          Loyalty: 20,
          Sportsmanship: 20,
          Controversy: 1,
        },
        attributes: { Determination: 20, Leadership: 20 },
      }),
    );
    expect(score).toBeCloseTo(HAS_SCORE_CEILING, 10);
  });
});

describe("hasBand", () => {
  it("maps practical range onto SD attr bands; overflow is super", () => {
    expect(HAS_PRACTICAL_FLOOR).toBe(3.5);
    expect(HAS_PRACTICAL_CEILING).toBeCloseTo(HAS_SCORE_CEILING - 2.5, 10);

    expect(hasBand(HAS_PRACTICAL_CEILING + 0.01)).toBe("super");
    expect(hasBand(HAS_PRACTICAL_FLOOR - 0.01)).toBe("low");
    expect(hasBand(HAS_PRACTICAL_FLOOR)).toBe("low");

    // Top of practical span → ~20 on mapped 1–20 → super
    expect(hasBand(HAS_PRACTICAL_CEILING)).toBe("super");
  });
});

describe("hasProgress", () => {
  it("fills as % of practical span; Super HAS fills more than Excellent PA", () => {
    expect(hasProgress(HAS_PRACTICAL_FLOOR)).toBe(0);
    expect(hasProgress(HAS_PRACTICAL_CEILING)).toBe(1);
    expect(hasProgress(HAS_PRACTICAL_CEILING + 1)).toBe(1);
    expect(hasProgress(HAS_PRACTICAL_FLOOR - 1)).toBe(0);

    const superHas = 15.6;
    expect(hasBand(superHas)).toBe("super");
    expect(hasProgress(superHas)).toBeGreaterThan(abilityProgress(180));
    expect(abilityToneFromScore(180)).toBe("high");
  });
});
