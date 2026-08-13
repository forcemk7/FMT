import { describe, expect, it } from "vitest";
import {
  HIDDEN_QUALITY_ELITE_TOP_FRACTION,
  HIDDEN_QUALITY_GOOD_FLOOR,
  fmEliteHasFloor,
  hiddenQualityFloorScore,
  hiddenQualityScore,
  hiddenQualityTone,
  invertControversy,
  loadCatalog,
  rankPersonalityMediaCombos,
  resolveEliteHasFloor,
  resolvePoorHasCeiling,
  toEstimate,
  uniqueHasBottomFractionCeiling,
  uniqueHasTopFractionFloor,
  type AttributeEstimates,
  HA_QUALITY_WEIGHT_SUM,
} from "../src/index.js";

function mids(values: Record<string, number>): AttributeEstimates {
  const entry = (n: number) => toEstimate({ min: n, max: n });
  return {
    professionalism: entry(values.professionalism ?? 10),
    pressure: entry(values.pressure ?? 10),
    importantMatches: {
      min: 1,
      max: 20,
      midpoint: Number.NaN,
      exact: false,
      unmodeled: true,
    },
    ambition: entry(values.ambition ?? 10),
    temperament: entry(values.temperament ?? 10),
    loyalty: entry(values.loyalty ?? 10),
    sportsmanship: entry(values.sportsmanship ?? 10),
    controversy: entry(values.controversy ?? 10),
  };
}

function bands(
  values: Record<string, { min: number; max: number }>,
): AttributeEstimates {
  const entry = (min: number, max: number) => toEstimate({ min, max });
  const fallback = { min: 10, max: 10 };
  const pick = (key: string) => values[key] ?? fallback;
  return {
    professionalism: entry(pick("professionalism").min, pick("professionalism").max),
    pressure: entry(pick("pressure").min, pick("pressure").max),
    importantMatches: {
      min: 1,
      max: 20,
      midpoint: Number.NaN,
      exact: false,
      unmodeled: true,
    },
    ambition: entry(pick("ambition").min, pick("ambition").max),
    temperament: entry(pick("temperament").min, pick("temperament").max),
    loyalty: entry(pick("loyalty").min, pick("loyalty").max),
    sportsmanship: entry(pick("sportsmanship").min, pick("sportsmanship").max),
    controversy: entry(pick("controversy").min, pick("controversy").max),
  };
}

describe("hiddenQualityScore", () => {
  it("weights Beni priorities and inverts controversy onto 1–20", () => {
    expect(
      hiddenQualityScore(
        mids({
          professionalism: 20,
          ambition: 20,
          pressure: 20,
          temperament: 20,
          loyalty: 20,
          sportsmanship: 20,
          controversy: 1,
        }),
      ),
    ).toBe(20);

    expect(
      hiddenQualityScore(
        mids({
          professionalism: 1,
          ambition: 1,
          pressure: 1,
          temperament: 1,
          loyalty: 1,
          sportsmanship: 1,
          controversy: 20,
        }),
      ),
    ).toBe(1);
  });

  it("folds known Det into HAS and demotes definite-low Det packs", () => {
    const attrs = mids({
      professionalism: 17.5,
      pressure: 17.5,
      ambition: 10.5,
      temperament: 10.5,
      loyalty: 10.5,
      sportsmanship: 20,
      controversy: 3,
    });
    const without = hiddenQualityScore(attrs);
    const withDet = hiddenQualityScore(attrs, { determination: 5 });
    // Honest-like: Det 1–9 mid 5 should pull HAS down vs unconstrained Det.
    expect(withDet).toBeLessThan(without);
    expect(withDet).toBeCloseTo((without * 21 + 5 * 5) / 26, 10);
  });

  it("ignores Det/Lead when not supplied", () => {
    expect(hiddenQualityScore(mids({}))).toBe(213 / HA_QUALITY_WEIGHT_SUM);
  });

  it("prefers Pro/Pre over Loy/Spo at equal unweighted sums", () => {
    const proHeavy = mids({
      professionalism: 18,
      temperament: 18,
      pressure: 18,
      ambition: 10,
      loyalty: 10,
      sportsmanship: 10,
      controversy: 10,
    });
    const loyHeavy = mids({
      professionalism: 10,
      temperament: 10,
      pressure: 10,
      ambition: 10,
      loyalty: 18,
      sportsmanship: 18,
      controversy: 2,
    });
    expect(hiddenQualityScore(proHeavy)).toBeGreaterThan(
      hiddenQualityScore(loyHeavy),
    );
  });
});

describe("invertControversy", () => {
  it("maps Con 1→20 and Con 20→1", () => {
    expect(invertControversy(1)).toBe(20);
    expect(invertControversy(20)).toBe(1);
    expect(invertControversy(10)).toBe(11);
  });
});

describe("hiddenQualityFloorScore", () => {
  it("uses mins and Con max (before invert) with the same weights", () => {
    const attrs = bands({
      professionalism: { min: 14, max: 18 },
      ambition: { min: 10, max: 12 },
      pressure: { min: 12, max: 16 },
      temperament: { min: 14, max: 16 },
      loyalty: { min: 8, max: 12 },
      sportsmanship: { min: 10, max: 14 },
      controversy: { min: 4, max: 8 },
    });
    // 5×14 + 4×12 + 3×10 + 3×14 + 2×8 + 1×10 + 3×(21−8) = 255
    expect(hiddenQualityFloorScore(attrs)).toBe(255 / HA_QUALITY_WEIGHT_SUM);
  });
});

describe("hiddenQualityTone / elite floor", () => {
  it("uses explicit elite / poor cuts for green and red", () => {
    expect(fmEliteHasFloor()).toBe(16);
    expect(HIDDEN_QUALITY_ELITE_TOP_FRACTION).toBe(0.25);
    expect(hiddenQualityTone(15, 14.5, 11)).toBe("good");
    expect(hiddenQualityTone(14.4, 14.5, 11)).toBe("neutral");
    expect(hiddenQualityTone(11, 14.5, 11)).toBe("bad");
    expect(hiddenQualityTone(5.9)).toBe("bad");
  });

  it("resolveEliteHasFloor takes the top 25% unique HAS cut", () => {
    // 10 unique scores → ceil(2.5) = top 3 values → floor is 17
    const scores = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19];
    expect(uniqueHasTopFractionFloor(scores, 0.25)).toBe(17);
    expect(resolveEliteHasFloor(scores)).toBe(17);
    // duplicates don't inflate the pool
    expect(resolveEliteHasFloor([...scores, 19, 19, 10])).toBe(17);
  });

  it("resolvePoorHasCeiling takes the bottom 25% unique HAS cut", () => {
    const scores = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19];
    expect(uniqueHasBottomFractionCeiling(scores, 0.25)).toBe(12);
    expect(resolvePoorHasCeiling(scores)).toBe(12);
    expect(resolvePoorHasCeiling([...scores, 10, 10, 19])).toBe(12);
  });

  it("marks a meaningful elite and poor band on the catalog", () => {
    const catalog = loadCatalog();
    for (const isRegen of [false, true]) {
      const ranking = rankPersonalityMediaCombos(catalog, { isRegen });
      const elite = ranking.entries.filter((e) => e.tone === "good");
      const poor = ranking.entries.filter((e) => e.tone === "bad");
      expect(ranking.eliteHasFloor).toBeLessThan(16);
      expect(ranking.eliteHasFloor).toBeGreaterThanOrEqual(
        HIDDEN_QUALITY_GOOD_FLOOR - 2,
      );
      expect(elite.length).toBeGreaterThan(4);
      expect(elite.length).toBeLessThan(ranking.entries.length / 2);
      expect(poor.length).toBeGreaterThan(4);
      expect(poor.length).toBeLessThan(ranking.entries.length / 2);
      for (const entry of elite) {
        expect(entry.haScore).toBeGreaterThanOrEqual(ranking.eliteHasFloor);
      }
      for (const entry of poor) {
        expect(entry.haScore).toBeLessThanOrEqual(ranking.poorHasCeiling);
      }
    }
  });
});
