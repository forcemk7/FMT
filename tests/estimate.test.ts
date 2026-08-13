import { describe, expect, it } from "vitest";
import {
  estimatePlayer,
  findMediaHandling,
  findPersonality,
  formatRange,
  isPersonalityMediaCompatible,
  loadCatalog,
  parseMediaHandlingInput,
  parseRange,
} from "../src/index.js";

describe("range parsing", () => {
  it("parses sheet spans and singles", () => {
    expect(parseRange("15-20")).toEqual({ min: 15, max: 20 });
    expect(parseRange("01 - 20")).toEqual({ min: 1, max: 20 });
    expect(parseRange("7")).toEqual({ min: 7, max: 7 });
    expect(parseRange("-")).toBeNull();
  });
});

describe("media handling labels", () => {
  it("expands abbreviations to full tags", () => {
    expect(parseMediaHandlingInput("MF, Unf")).toEqual([
      "Media-friendly",
      "Unflappable",
    ]);
    expect(parseMediaHandlingInput("Out, ST, Con")).toEqual([
      "Outspoken",
      "Short-tempered",
      "Confrontational",
    ]);
    expect(parseMediaHandlingInput("Evasive, Reserved")).toEqual([
      "Evasive",
      "Reserved",
    ]);
  });

  it("matches in-game order and accepts reverse order", () => {
    const catalog = loadCatalog();
    const forward = findMediaHandling(catalog, "Unflappable, Media-friendly");
    const reverse = findMediaHandling(catalog, "Media-friendly, Unflappable");
    expect(forward?.id).toBe("Unflappable, Media-friendly");
    expect(reverse?.id).toBe("Unflappable, Media-friendly");
    expect(
      findMediaHandling(catalog, "Volatile, Media-friendly, Confrontational")?.id,
    ).toBe("Volatile, Media-friendly, Confrontational");
    expect(
      findMediaHandling(catalog, "Media-friendly, Volatile, Confrontational")?.id,
    ).toBe("Volatile, Media-friendly, Confrontational");
  });
});

describe("catalog", () => {
  const catalog = loadCatalog();

  it("loads all personalities and media rows", () => {
    expect(catalog.personalities.length).toBe(39);
    expect(catalog.mediaHandling.length).toBe(31);
    expect(catalog.cases.length).toBe(6);
  });

  it("aliases Very Loyal / Devoted", () => {
    const row = catalog.personalities.find((p) => p.id === "Very Loyal");
    expect(row?.aliases).toContain("Devoted");
    expect(findPersonality(catalog, "Devoted").id).toBe("Very Loyal");
  });

  it("uses in-game Lacking in… personality names", () => {
    expect(
      catalog.personalities.find((p) => p.id === "Lacking in Determination"),
    ).toBeTruthy();
    expect(
      catalog.personalities.find((p) => p.id === "Lacking in Self-Belief"),
    ).toBeTruthy();
    expect(findPersonality(catalog, "Low Determination").id).toBe(
      "Lacking in Determination",
    );
    expect(findPersonality(catalog, "Low Self Belief").id).toBe(
      "Lacking in Self-Belief",
    );
  });
});

describe("estimatePlayer — Spirited + Unflappable, Media-friendly", () => {
  const catalog = loadCatalog();

  it("intersects base bands (checker example inputs)", () => {
    const result = estimatePlayer(catalog, {
      personality: "Spirited",
      mediaHandling: "MF, Unf",
      determination: 15,
      isRegen: true,
    });

    expect(result.player.mediaHandling).toBe("Unflappable, Media-friendly");
    expect(formatRange(result.attributes.professionalism)).toBe("11-17");
    expect(result.player.determination).toBe(15);
    expect(result.attributes).not.toHaveProperty("determination");
    expect(result.attributes).not.toHaveProperty("leadership");
    expect(formatRange(result.attributes.pressure)).toBe("15-20");
    expect(formatRange(result.attributes.temperament)).toBe("15-20");
    expect(formatRange(result.attributes.sportsmanship)).toBe("5-14");
    expect(formatRange(result.attributes.controversy)).toBe("1-14");
  });

  it("warns when known determination is outside the personality band", () => {
    const result = estimatePlayer(catalog, {
      personality: "Spirited",
      mediaHandling: "MF, Unf",
      determination: 20,
      isRegen: true,
    });

    expect(result.warnings.some((w) => w.includes("Determination 20"))).toBe(
      true,
    );
  });
});

describe("estimatePlayer — Fairly Professional + Reserved (sheet parity)", () => {
  const catalog = loadCatalog();

  it("matches spreadsheet ranges for regen Hwang Soo-Hwan inputs", () => {
    const result = estimatePlayer(catalog, {
      personality: "Fairly Professional",
      mediaHandling: "Reserved",
      determination: 13,
      leadership: 6,
      age: 24,
      isRegen: true,
    });

    expect(formatRange(result.attributes.professionalism)).toBe("15-20");
    expect(formatRange(result.attributes.ambition)).toBe("6-20");
    expect(formatRange(result.attributes.pressure)).toBe("1-14");
    expect(formatRange(result.attributes.temperament)).toBe("7-20");
    expect(formatRange(result.attributes.loyalty)).toBe("11-20");
    expect(formatRange(result.attributes.sportsmanship)).toBe("5-20");
    expect(formatRange(result.attributes.controversy)).toBe("1-5");
    expect(result.unsatisfiableCases).toEqual([]);
  });
});

describe("estimatePlayer — progressive (partial signals)", () => {
  const catalog = loadCatalog();

  it("estimates from personality alone before media is chosen", () => {
    const partial = estimatePlayer(catalog, {
      personality: "Spirited",
      isRegen: true,
    });
    expect(partial.partial).toBe(true);
    expect(partial.player.mediaHandling).toBeUndefined();
    expect(formatRange(partial.attributes.professionalism)).toBe("11-17");
    expect(formatRange(partial.attributes.temperament)).toBe("10-20");

    const full = estimatePlayer(catalog, {
      personality: "Spirited",
      mediaHandling: "MF, Unf",
      isRegen: true,
    });
    expect(full.partial).toBe(false);
    expect(formatRange(full.attributes.temperament)).toBe("15-20");
  });

  it("estimates from media alone before personality is chosen", () => {
    const result = estimatePlayer(catalog, {
      mediaHandling: "Reserved",
      isRegen: true,
    });
    expect(result.partial).toBe(true);
    expect(result.player.personality).toBeUndefined();
    expect(formatRange(result.attributes.controversy)).toBe("1-5");
  });
});

describe("estimatePlayer — Outspoken media cases", () => {
  const catalog = loadCatalog();

  it("applies Outspoken controversy definite", () => {
    const result = estimatePlayer(catalog, {
      personality: "Ambitious",
      mediaHandling: "Outspoken",
    });

    expect(formatRange(result.attributes.controversy)).toBe("15-20");
    expect(result.attributes.temperament.min).toBe(7);
    expect(result.unsatisfiableCases).toEqual([]);
  });
});

describe("estimatePlayer — impossible personality × media combos", () => {
  const catalog = loadCatalog();

  it("keeps inverted Temperament 15-14 for Model Citizen + Evasive, Reserved", () => {
    const result = estimatePlayer(catalog, {
      personality: "Model Citizen",
      mediaHandling: "Evasive, Reserved",
    });

    expect(formatRange(result.attributes.temperament)).toBe("15-14");
    expect(result.attributes.temperament.impossible).toBe(true);
    expect(result.contradictions).toContain("temperament");
    expect(result.impossibleCombo).toBe(true);
    expect(result.warnings.some((w) => /Impossible personality \/ media combo/i.test(w))).toBe(
      true,
    );
  });

  it("marks Model Citizen + Unflappable, Media-friendly impossible (case 2)", () => {
    const result = estimatePlayer(catalog, {
      personality: "Model Citizen",
      mediaHandling: "Unflappable, Media-friendly",
    });

    expect(result.unsatisfiableCases).toContain(2);
    expect(result.impossibleCombo).toBe(true);
    expect(
      result.warnings.some((w) => /unsatisfiable media case/i.test(w)),
    ).toBe(true);
  });

  it("accepts known Model Citizen media styles from the player DB", () => {
    for (const media of [
      "Unflappable",
      "Reserved",
      "Level-Headed",
      "Evasive, Unflappable",
    ]) {
      const result = estimatePlayer(catalog, {
        personality: "Model Citizen",
        mediaHandling: media,
      });
      expect(result.impossibleCombo, media).toBe(false);
      expect(result.attributes.temperament.min).toBeLessThanOrEqual(
        result.attributes.temperament.max,
      );
    }
  });

  it("marks Evasive (alone) incompatible with Model Citizen via band check", () => {
    const citizen = catalog.personalities.find((p) => p.id === "Model Citizen")!;
    const evasive = catalog.mediaHandling.find((m) => m.id === "Evasive")!;
    const reservedCombo = catalog.mediaHandling.find(
      (m) => m.id === "Evasive, Reserved",
    )!;
    expect(isPersonalityMediaCompatible(citizen, evasive)).toBe(false);
    expect(isPersonalityMediaCompatible(citizen, reservedCombo)).toBe(false);
  });
});
