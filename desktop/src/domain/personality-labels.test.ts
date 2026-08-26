import { describe, expect, it } from "vitest";
import { loadCatalog } from "../ha/catalog/lookup";
import { comboFeasibleForAttrs } from "../ha/inference/match-combo";
import { matchBestPersonalityCombo } from "../ha/match-best";
import { livePersonalityLabels } from "./personality-labels";
import type { LivePlayer } from "./adapters";

const catalog = loadCatalog();

/** Levels that pass Level-Headed cases but fail Media-friendly case 2. */
const highProHighSpoHighLoy = {
  loyalty: 15,
  professionalism: 16,
  sportsmanship: 14,
  pressure: 12,
  temperament: 12,
  controversy: 8,
  ambition: 14,
};

/** Gilson HA pack (FM Light-Hearted / Evasive, Reserved; Det 14 / Lea 16). */
const gilsonHaPack = {
  ambition: 15,
  loyalty: 15,
  pressure: 18,
  professionalism: 16,
  sportsmanship: 16,
  temperament: 13,
  controversy: 5,
};

function player(partial: Partial<LivePlayer>): LivePlayer {
  return {
    id: "1",
    name: "Test",
    age: 24,
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

describe("comboFeasibleForAttrs — media case point matching", () => {
  it("Driven + high Loy/Pro/Spo fits Level-Headed, not Media-friendly", () => {
    const attrs = { ...highProHighSpoHighLoy, determination: 18, leadership: 15 };
    expect(comboFeasibleForAttrs(catalog, "Driven", "Level-Headed", attrs)).toBe(true);
    expect(comboFeasibleForAttrs(catalog, "Driven", "Media-friendly", attrs)).toBe(false);
  });

  it("Resilient + case-6 Pro/Spo fits Unflappable, not Unflappable+MF", () => {
    const attrs = {
      determination: 15,
      leadership: 17,
      ambition: 12,
      loyalty: 15,
      pressure: 18,
      temperament: 16,
      controversy: 7,
      professionalism: 15,
      sportsmanship: 14,
    };
    expect(comboFeasibleForAttrs(catalog, "Resilient", "Unflappable", attrs)).toBe(true);
    expect(
      comboFeasibleForAttrs(catalog, "Resilient", "Unflappable, Media-friendly", attrs),
    ).toBe(false);
  });
});

describe("comboFeasibleForAttrs — Born Leader requires known Det/Lea=20 (T013)", () => {
  it("refuses Born Leader when Det or Lea is missing", () => {
    expect(
      comboFeasibleForAttrs(catalog, "Born Leader", "Evasive, Reserved", {
        ...gilsonHaPack,
        determination: 20,
      }),
    ).toBe(false);
    expect(
      comboFeasibleForAttrs(catalog, "Born Leader", "Evasive, Reserved", gilsonHaPack),
    ).toBe(false);
  });

  it("Gilson Det 14 / Lea 16 fits Light Hearted × Evasive, Reserved, not Born Leader", () => {
    const attrs = { ...gilsonHaPack, determination: 14, leadership: 16 };
    expect(
      comboFeasibleForAttrs(catalog, "Born Leader", "Evasive, Reserved", attrs),
    ).toBe(false);
    expect(
      comboFeasibleForAttrs(catalog, "Light Hearted", "Evasive, Reserved", attrs),
    ).toBe(true);
  });
});

describe("matchBestPersonalityCombo", () => {
  it("picks Light-Hearted × Evasive, Reserved for Gilson pack", () => {
    const labels = matchBestPersonalityCombo({
      ...gilsonHaPack,
      determination: 14,
      leadership: 16,
      isRegen: false,
      age: 24,
    });
    expect(labels).toEqual({
      personality: "Light-Hearted",
      mediaHandling: "Evasive, Reserved",
    });
  });
});

describe("livePersonalityLabels", () => {
  it("infers labels from live personalityAttributes + Det/Lea", () => {
    const labels = livePersonalityLabels(
      player({
        attributes: { Determination: 14, Leadership: 16 },
        personalityAttributes: {
          Ambition: 15,
          Loyalty: 15,
          Pressure: 18,
          Professionalism: 16,
          Sportsmanship: 16,
          Temperament: 13,
          Controversy: 5,
        },
      }),
    );
    expect(labels).toEqual({
      personality: "Light-Hearted",
      mediaHandling: "Evasive, Reserved",
    });
  });

  it("returns null when the personality pack is incomplete", () => {
    expect(
      livePersonalityLabels(
        player({
          personalityAttributes: { Professionalism: 16, Ambition: 15 },
        }),
      ),
    ).toBeNull();
  });
});
