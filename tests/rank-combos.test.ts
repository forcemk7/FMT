import { describe, expect, it } from "vitest";
import {
  isPersonalityMediaCompatible,
  loadCatalog,
  rankPersonalityMediaCombos,
  rankPersonalityMediaCombosUnified,
} from "../src/index.js";

describe("personality × media ranker", () => {
  const catalog = loadCatalog();

  it("ranks only compatible combos by HA index descending", () => {
    const ranking = rankPersonalityMediaCombos(catalog, { isRegen: true });

    expect(ranking.isRegen).toBe(true);
    expect(ranking.entries.length).toBeGreaterThan(10);
    expect(ranking.entries[0]?.rank).toBe(1);

    for (let i = 1; i < ranking.entries.length; i++) {
      const prev = ranking.entries[i - 1]!;
      const curr = ranking.entries[i]!;
      expect(curr.rank).toBe(i + 1);
      if (curr.haScore === prev.haScore) {
        expect(curr.floorScore).toBeLessThanOrEqual(prev.floorScore);
      } else {
        expect(curr.haScore).toBeLessThan(prev.haScore);
      }
    }

    for (const entry of ranking.entries) {
      const personality = catalog.personalities.find(
        (p) => p.id === entry.personality,
      )!;
      const media = catalog.mediaHandling.find(
        (m) => m.styles.join(", ") === entry.mediaHandling,
      )!;
      expect(isPersonalityMediaCompatible(personality, media)).toBe(true);
      expect(Number.isFinite(entry.haScore)).toBe(true);
      expect(Number.isFinite(entry.floorScore)).toBe(true);
      expect(entry.haScore).toBeGreaterThanOrEqual(1);
      expect(entry.haScore).toBeLessThanOrEqual(20);
    }
  });

  it("excludes regen-only personalities from the non-regen list", () => {
    const nonRegen = rankPersonalityMediaCombos(catalog, { isRegen: false });
    const regen = rankPersonalityMediaCombos(catalog, { isRegen: true });

    expect(nonRegen.isRegen).toBe(false);
    expect(regen.entries.length).toBeGreaterThan(nonRegen.entries.length);

    const regenOnlyIds = new Set(
      catalog.personalities
        .filter((p) => p.conditionals.some((r) => r.kind === "regen_only"))
        .map((p) => p.id),
    );
    expect(
      nonRegen.entries.some((e) => regenOnlyIds.has(e.personality)),
    ).toBe(false);
  });

  it("excludes Model Citizen + Evasive, Reserved", () => {
    const ranking = rankPersonalityMediaCombos(catalog, { isRegen: true });
    expect(
      ranking.entries.some(
        (e) =>
          e.personality === "Model Citizen" &&
          e.mediaHandling === "Evasive, Reserved",
      ),
    ).toBe(false);
  });

  it("excludes Model Citizen + Unflappable, Media-friendly (unsatisfiable case 2)", () => {
    const ranking = rankPersonalityMediaCombos(catalog, { isRegen: true });
    expect(
      ranking.entries.some(
        (e) =>
          e.personality === "Model Citizen" &&
          e.mediaHandling === "Unflappable, Media-friendly",
      ),
    ).toBe(false);
  });

  it("unified mixed list labels only when REAL and NEWGEN HA differ", () => {
    const mixed = rankPersonalityMediaCombosUnified(catalog, {
      population: "mixed",
    });
    const realOnly = rankPersonalityMediaCombos(catalog, { isRegen: false });
    const regenOnly = rankPersonalityMediaCombos(catalog, { isRegen: true });

    const realHa = new Map(
      realOnly.entries.map((e) => [`${e.personality}\0${e.mediaHandling}`, e.haScore]),
    );
    const regenHa = new Map(
      regenOnly.entries.map((e) => [
        `${e.personality}\0${e.mediaHandling}`,
        e.haScore,
      ]),
    );

    for (const entry of mixed.entries) {
      expect(entry.mids.importantMatches).toBeNull();
      expect(entry.bands.importantMatches).toBeNull();
      expect(entry.bands.professionalism).toEqual({
        min: expect.any(Number),
        max: expect.any(Number),
      });
      const key = `${entry.personality}\0${entry.mediaHandling}`;
      const real = realHa.get(key);
      const regen = regenHa.get(key);
      if (real !== undefined && regen !== undefined && Math.abs(real - regen) < 1e-9) {
        expect(entry.label ?? null).toBeNull();
      } else if (real !== undefined && regen !== undefined) {
        expect(entry.label === "REAL" || entry.label === "NEWGEN").toBe(true);
      } else if (regen !== undefined) {
        expect(entry.label).toBe("NEWGEN");
      } else {
        expect(entry.label).toBe("REAL");
      }
    }

    const labeledPairs = mixed.entries.filter((e) => e.label);
    expect(labeledPairs.length).toBeGreaterThan(0);

    const realFilter = rankPersonalityMediaCombosUnified(catalog, {
      population: "real",
    });
    expect(realFilter.entries.every((e) => e.label !== "NEWGEN")).toBe(true);

    const newgenFilter = rankPersonalityMediaCombosUnified(catalog, {
      population: "newgen",
    });
    expect(newgenFilter.entries.every((e) => e.label !== "REAL")).toBe(true);
  });

  it("demotes definite-low Det packs (Honest / Sporting) out of elite", () => {
    const ranking = rankPersonalityMediaCombosUnified(catalog, {
      population: "mixed",
    });
    const lowDet = ranking.entries.filter(
      (e) =>
        (e.personality === "Honest" || e.personality === "Sporting") &&
        e.mids.determination !== null &&
        e.mids.determination <= 5,
    );
    expect(lowDet.length).toBeGreaterThan(0);
    for (const entry of lowDet) {
      expect(entry.tone).not.toBe("good");
      expect(entry.haScore).toBeLessThan(ranking.eliteHasFloor);
    }
  });
});
