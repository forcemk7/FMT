import { describe, expect, it } from "vitest";
import {
  comboFeasibleForAttrs,
  loadCatalog,
} from "../src/index.js";

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

describe("comboFeasibleForAttrs — media case point matching", () => {
  it("Driven + high Loy/Pro/Spo fits Level-Headed, not Media-friendly (Gabor)", () => {
    const attrs = { ...highProHighSpoHighLoy, determination: 18, leadership: 15 };
    expect(
      comboFeasibleForAttrs(catalog, "Driven", "Level-Headed", attrs),
    ).toBe(true);
    expect(
      comboFeasibleForAttrs(catalog, "Driven", "Media-friendly", attrs),
    ).toBe(false);
  });

  it("Resilient + case-6 Pro/Spo fits Unflappable, not Unflappable+MF (Yoan)", () => {
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
    expect(
      comboFeasibleForAttrs(catalog, "Resilient", "Unflappable", attrs),
    ).toBe(true);
    expect(
      comboFeasibleForAttrs(
        catalog,
        "Resilient",
        "Unflappable, Media-friendly",
        attrs,
      ),
    ).toBe(false);
  });

  it("Spirited + case-6 fits Unflappable, not Unflappable+MF (Pietro)", () => {
    const attrs = {
      determination: 16,
      leadership: 9,
      ambition: 13,
      loyalty: 14,
      pressure: 16,
      temperament: 15,
      controversy: 6,
      professionalism: 14,
      sportsmanship: 13,
    };
    expect(
      comboFeasibleForAttrs(catalog, "Spirited", "Unflappable", attrs),
    ).toBe(true);
    expect(
      comboFeasibleForAttrs(
        catalog,
        "Spirited",
        "Unflappable, Media-friendly",
        attrs,
      ),
    ).toBe(false);
  });

  it("Ambitious + high Pre/Tem + low Loy fits Unflappable+MF, not Media-friendly (Rodrigo)", () => {
    const attrs = {
      determination: 16,
      leadership: 12,
      ambition: 17,
      loyalty: 8,
      pressure: 16,
      temperament: 16,
      controversy: 9,
      professionalism: 14,
      sportsmanship: 12,
    };
    expect(
      comboFeasibleForAttrs(
        catalog,
        "Ambitious",
        "Unflappable, Media-friendly",
        attrs,
      ),
    ).toBe(true);
    expect(
      comboFeasibleForAttrs(catalog, "Ambitious", "Media-friendly", attrs),
    ).toBe(false);
  });

  it("Resolute Det 17 + Level-Headed attrs fits Resolute·LH, not Driven (Koné with correct Det)", () => {
    const attrs = {
      ...highProHighSpoHighLoy,
      determination: 17,
      leadership: 16,
      professionalism: 17,
      pressure: 8,
      sportsmanship: 12,
      temperament: 12,
      controversy: 8,
      ambition: 16,
    };
    expect(
      comboFeasibleForAttrs(catalog, "Resolute", "Level-Headed", attrs),
    ).toBe(true);
    expect(
      comboFeasibleForAttrs(catalog, "Driven", "Media-friendly", attrs),
    ).toBe(false);
    expect(
      comboFeasibleForAttrs(catalog, "Driven", "Level-Headed", attrs),
    ).toBe(false);
  });

  it("keeps Model Citizen · Unflappable (Santiago control — no Unf+MF)", () => {
    const attrs = {
      determination: 15,
      leadership: 11,
      ambition: 15,
      loyalty: 15,
      pressure: 16,
      temperament: 16,
      controversy: 5,
      professionalism: 18,
      sportsmanship: 16,
    };
    expect(
      comboFeasibleForAttrs(catalog, "Model Citizen", "Unflappable", attrs),
    ).toBe(true);
    expect(
      comboFeasibleForAttrs(
        catalog,
        "Model Citizen",
        "Unflappable, Media-friendly",
        attrs,
      ),
    ).toBe(false);
  });

  it("keeps Resolute · Media-friendly when Loy is low (Nathan/Marko family)", () => {
    const attrs = {
      determination: 16,
      leadership: 16,
      ambition: 14,
      loyalty: 8,
      pressure: 12,
      temperament: 12,
      controversy: 8,
      professionalism: 16,
      sportsmanship: 10,
    };
    expect(
      comboFeasibleForAttrs(catalog, "Resolute", "Media-friendly", attrs),
    ).toBe(true);
    expect(
      comboFeasibleForAttrs(catalog, "Resolute", "Level-Headed", attrs),
    ).toBe(false);
  });

  it("Mercenary is regen-only (Přibyl: Amb 16 Loy 3)", () => {
    const attrs = {
      determination: 14,
      ambition: 16,
      loyalty: 3,
      professionalism: 14,
      pressure: 7,
      sportsmanship: 11,
      temperament: 11,
      controversy: 10,
    };
    expect(
      comboFeasibleForAttrs(catalog, "Mercenary", "Media-friendly", {
        ...attrs,
        isRegen: false,
      }),
    ).toBe(false);
    expect(
      comboFeasibleForAttrs(catalog, "Mercenary", "Media-friendly", {
        ...attrs,
        isRegen: true,
      }),
    ).toBe(true);
    expect(
      comboFeasibleForAttrs(catalog, "Ambitious", "Media-friendly", {
        ...attrs,
        isRegen: false,
      }),
    ).toBe(true);
  });
});

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

describe("comboFeasibleForAttrs — Born Leader requires known Det/Lea=20 (T013)", () => {
  it("refuses Born Leader when Det or Lea is missing", () => {
    expect(
      comboFeasibleForAttrs(catalog, "Born Leader", "Evasive, Reserved", {
        ...gilsonHaPack,
        determination: 20,
        // leadership missing
      }),
    ).toBe(false);
    expect(
      comboFeasibleForAttrs(catalog, "Born Leader", "Evasive, Reserved", {
        ...gilsonHaPack,
        leadership: 20,
        // determination missing
      }),
    ).toBe(false);
    expect(
      comboFeasibleForAttrs(catalog, "Born Leader", "Evasive, Reserved", {
        ...gilsonHaPack,
        // both missing — must not stay feasible on tight 20/20 bands
      }),
    ).toBe(false);
  });

  it("refuses Born Leader when Det/Lea are known but not 20 (Gilson)", () => {
    expect(
      comboFeasibleForAttrs(catalog, "Born Leader", "Evasive, Reserved", {
        ...gilsonHaPack,
        determination: 14,
        leadership: 16,
      }),
    ).toBe(false);
  });

  it("accepts Born Leader only with known Det=20 and Lea=20", () => {
    expect(
      comboFeasibleForAttrs(catalog, "Born Leader", "Evasive, Reserved", {
        ...gilsonHaPack,
        determination: 20,
        leadership: 20,
      }),
    ).toBe(true);
  });

  it("Gilson Det 14 / Lea 16 fits Light Hearted × Evasive, Reserved, not Born Leader", () => {
    const attrs = {
      ...gilsonHaPack,
      determination: 14,
      leadership: 16,
    };
    expect(
      comboFeasibleForAttrs(catalog, "Born Leader", "Evasive, Reserved", attrs),
    ).toBe(false);
    expect(
      comboFeasibleForAttrs(
        catalog,
        "Light Hearted",
        "Evasive, Reserved",
        attrs,
      ),
    ).toBe(true);
  });
});
