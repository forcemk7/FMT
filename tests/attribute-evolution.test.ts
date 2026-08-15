import { describe, expect, it } from "vitest";
import type { AttributeHistoryPoint } from "../shared/save/types.ts";
import {
  attrValueAndDelta,
  defaultHaEvolutionAttrIds,
  evoChipValueTone,
  evoVisibilityOverrideFromSelect,
  evoVisibilitySelectValue,
  formatAttrDelta,
  isHaProgressAttrId,
  splitEvolutionChartSelection,
  type EvolutionAttrId,
} from "../web/attribute-evolution.ts";
import { haSnapshotsToHistoryPoints } from "../web/ha-history-store.ts";

const ID = "general.professionalism" as const;

function point(
  index: number,
  professionalism: number | null,
): AttributeHistoryPoint {
  return {
    index,
    general:
      professionalism == null ? {} : { professionalism },
  };
}

describe("attrValueAndDelta", () => {
  it("recent is last two finite points; 0/missing delta is null", () => {
    const two = [point(0, 12), point(1, 14)];
    expect(attrValueAndDelta(two, ID)).toEqual({ value: 14, delta: 2 });
    expect(attrValueAndDelta(two, ID, null, "recent")).toEqual({
      value: 14,
      delta: 2,
    });

    const flat = [point(0, 12), point(1, 12)];
    expect(attrValueAndDelta(flat, ID, null, "recent")).toEqual({
      value: 12,
      delta: null,
    });

    const one = [point(0, 12)];
    expect(attrValueAndDelta(one, ID, null, "recent")).toEqual({
      value: 12,
      delta: null,
    });
  });

  it("allTime is first finite vs latest; empty progress 0 uses 1", () => {
    const yoan = [point(0, 12), point(1, 14), point(2, 18)];
    expect(attrValueAndDelta(yoan, ID, null, "recent")).toEqual({
      value: 18,
      delta: 4,
    });
    expect(attrValueAndDelta(yoan, ID, null, "allTime")).toEqual({
      value: 18,
      delta: 6,
    });

    const empty0 = [
      point(0, null),
      point(1, 12),
      point(2, 14),
      point(3, 18),
    ];
    expect(attrValueAndDelta(empty0, ID, null, "recent")).toEqual({
      value: 18,
      delta: 4,
    });
    expect(attrValueAndDelta(empty0, ID, null, "allTime")).toEqual({
      value: 18,
      delta: 6,
    });
  });

  it("formatAttrDelta is empty when missing so the reserved delta slot stays blank", () => {
    expect(formatAttrDelta(null)).toBe("");
    expect(formatAttrDelta(0)).toBe("");
    expect(formatAttrDelta(2)).toBe("+2");
    expect(formatAttrDelta(-3)).toBe("-3");
    expect(formatAttrDelta(12)).toBe("+12");
  });

  it("visibility select idle is default (-); Show all / Hide all are explicit", () => {
    expect(evoVisibilitySelectValue("default")).toBe("default");
    expect(evoVisibilitySelectValue("all")).toBe("all");
    expect(evoVisibilitySelectValue("none")).toBe("none");
    expect(evoVisibilityOverrideFromSelect("default")).toBe("default");
    expect(evoVisibilityOverrideFromSelect("all")).toBe("all");
    expect(evoVisibilityOverrideFromSelect("none")).toBe("none");
  });
});

describe("evoChipValueTone", () => {
  it("matches HA table: Pro 18 good, CON 18 bad, 12 uncolored", () => {
    expect(evoChipValueTone("general.professionalism", 18)).toBe("good");
    expect(evoChipValueTone("general.controversy", 18)).toBe("bad");
    expect(evoChipValueTone("general.controversy", 3)).toBe("good");
    expect(evoChipValueTone("general.professionalism", 12)).toBe("");
    expect(evoChipValueTone("general.professionalism", null)).toBe("");
  });

  it("non-HA 1–20 attrs use the same floors; CON invert only on controversy", () => {
    expect(evoChipValueTone("technical.finishing", 18)).toBe("good");
    expect(evoChipValueTone("technical.finishing", 3)).toBe("bad");
    expect(evoChipValueTone("technical.finishing", 12)).toBe("");
    expect(evoChipValueTone("mental.determination", 18)).toBe("good");
  });
});

const DET = "mental.determination" as const;

function detPoint(
  index: number,
  determination: number,
  date: string,
): AttributeHistoryPoint {
  return {
    index,
    date,
    mental: { determination },
    general: { professionalism: 16 },
  };
}

function historyForAttr(
  ha: AttributeHistoryPoint[],
  ca: AttributeHistoryPoint[],
  id: EvolutionAttrId,
): AttributeHistoryPoint[] {
  return isHaProgressAttrId(id) ? ha : ca;
}

function chartForSelection(
  ha: AttributeHistoryPoint[],
  ca: AttributeHistoryPoint[],
  selected: EvolutionAttrId[],
): { history: AttributeHistoryPoint[]; attrs: EvolutionAttrId[] } {
  const { caIds, haIds } = splitEvolutionChartSelection(selected);
  if (caIds.length > 0) return { history: ca, attrs: caIds };
  return { history: ha, attrs: haIds };
}

describe("Det/Lea Progress CA strip", () => {
  it("two CA dates 14 → 16: Recent and All time Det are +2", () => {
    const history = [detPoint(0, 14, "2039-11-07"), detPoint(1, 16, "2039-12-01")];
    expect(attrValueAndDelta(history, DET, null, "recent")).toEqual({
      value: 16,
      delta: 2,
    });
    expect(attrValueAndDelta(history, DET, null, "allTime")).toEqual({
      value: 16,
      delta: 2,
    });
  });

  it("three CA dates 14 → 15 → 17: Recent +2, All time +3", () => {
    const history = [
      detPoint(0, 14, "2039-11-07"),
      detPoint(1, 15, "2039-12-01"),
      detPoint(2, 17, "2040-01-15"),
    ];
    expect(attrValueAndDelta(history, DET, null, "recent")).toEqual({
      value: 17,
      delta: 2,
    });
    expect(attrValueAndDelta(history, DET, null, "allTime")).toEqual({
      value: 17,
      delta: 3,
    });
  });

  it("Pro–Con stay on the pack general nest of HA snapshots", () => {
    const history = haSnapshotsToHistoryPoints([
      {
        gameDate: "2039-11-07",
        extractedAt: "2026-08-11T01:00:00.000Z",
        values: { professionalism: 16 },
        mental: { determination: 14 },
      },
      {
        gameDate: "2039-12-01",
        extractedAt: "2026-08-11T08:00:00.000Z",
        values: { professionalism: 18 },
        mental: { determination: 16 },
      },
    ]);
    expect(attrValueAndDelta(history, "general.professionalism", null, "allTime")).toEqual({
      value: 18,
      delta: 2,
    });
  });

  it("CA/tech chips still read the in-save strip (one-tip after compact)", () => {
    const strip: AttributeHistoryPoint[] = [
      { index: 0, technical: { finishing: 12 }, mental: { determination: 14 } },
    ];
    expect(attrValueAndDelta(strip, "technical.finishing", null, "recent")).toEqual({
      value: 12,
      delta: null,
    });
    expect(attrValueAndDelta(strip, DET, null, "recent")).toEqual({
      value: 14,
      delta: null,
    });
  });

  it("FT CA strip ≥2 Det: Det uses the strip even with one HA date; pack stays HA", () => {
    const ha = haSnapshotsToHistoryPoints([
      {
        gameDate: "2039-07-25",
        extractedAt: "2026-08-14T01:00:00.000Z",
        values: { professionalism: 16 },
        mental: { determination: 16 },
      },
    ]);
    const strip: AttributeHistoryPoint[] = [
      { index: 0, date: "2039-09-01", mental: { determination: 14, leadership: 8 } },
      { index: 1, date: "2039-12-01", mental: { determination: 16, leadership: 8 } },
    ];
    expect(historyForAttr(ha, strip, DET)).toBe(strip);
    expect(historyForAttr(ha, strip, "general.professionalism")).toBe(ha);
    expect(attrValueAndDelta(strip, DET, null, "allTime")).toEqual({
      value: 16,
      delta: 2,
    });
  });

  it("II/U19 tip-only Det stays one CA point; pack stays HA", () => {
    const ha = haSnapshotsToHistoryPoints([
      {
        gameDate: "2039-12-01",
        extractedAt: "2026-08-14T01:00:00.000Z",
        values: { professionalism: 14, ambition: 12 },
        mental: { determination: 15 },
      },
    ]);
    const tip: AttributeHistoryPoint[] = [
      { index: 0, mental: { determination: 15 } },
    ];
    expect(historyForAttr(ha, tip, DET)).toBe(tip);
    expect(historyForAttr(ha, tip, "general.professionalism")).toBe(ha);
    expect(attrValueAndDelta(tip, DET, null, "recent")).toEqual({
      value: 15,
      delta: null,
    });
    const packOnly = chartForSelection(ha, tip, ["general.professionalism"]);
    expect(packOnly.history).toBe(ha);
    expect(packOnly.attrs).toEqual(["general.professionalism"]);
    const detChart = chartForSelection(ha, tip, [
      DET,
      "general.professionalism",
    ]);
    expect(detChart.history).toBe(tip);
    expect(detChart.attrs).toEqual([DET]);
    expect(detChart.history).toHaveLength(1);
  });

  it("HA ≥2 dates does not steal Det/Lea off the CA strip", () => {
    const ha = haSnapshotsToHistoryPoints([
      {
        gameDate: "2039-11-07",
        extractedAt: "2026-08-11T01:00:00.000Z",
        values: { professionalism: 16 },
        mental: { determination: 6 },
      },
      {
        gameDate: "2039-12-01",
        extractedAt: "2026-08-11T08:00:00.000Z",
        values: { professionalism: 16 },
        mental: { determination: 6 },
      },
    ]);
    const strip: AttributeHistoryPoint[] = [
      { index: 0, mental: { determination: 10 } },
      { index: 1, mental: { determination: 12 } },
      { index: 2, mental: { determination: 16 } },
    ];
    expect(historyForAttr(ha, strip, DET)).toBe(strip);
    expect(attrValueAndDelta(ha, DET, null, "allTime")).toEqual({
      value: 6,
      delta: null,
    });
    expect(attrValueAndDelta(strip, DET, null, "allTime")).toEqual({
      value: 16,
      delta: 6,
    });
    const mixed = chartForSelection(ha, strip, [
      DET,
      "general.professionalism",
    ]);
    expect(mixed.history).toBe(strip);
    expect(mixed.attrs).toEqual([DET]);
    expect(mixed.history).toHaveLength(3);
    const packOnly = chartForSelection(ha, strip, [
      "general.professionalism",
    ]);
    expect(packOnly.history).toBe(ha);
    expect(packOnly.attrs).toEqual(["general.professionalism"]);
    expect(packOnly.history).toHaveLength(2);
  });

  it("selecting Det charts the CA strip, not pack on that x", () => {
    const ha = haSnapshotsToHistoryPoints([
      {
        gameDate: "2039-07-25",
        extractedAt: "2026-08-14T01:00:00.000Z",
        values: { professionalism: 16 },
        mental: { determination: 16, leadership: 8 },
      },
    ]);
    const strip: AttributeHistoryPoint[] = [
      { index: 0, mental: { determination: 14, leadership: 8 } },
      { index: 1, mental: { determination: 16, leadership: 8 } },
    ];
    const chart = chartForSelection(ha, strip, [
      DET,
      "mental.leadership",
      "general.professionalism",
    ]);
    expect(chart.history).toBe(strip);
    expect(chart.attrs).toEqual([DET, "mental.leadership"]);
    expect(chart.history).toHaveLength(2);
  });

  it("Yoan-class pack change: two HA dates yield a non-empty All-time delta and ≥2 x", () => {
    const history = haSnapshotsToHistoryPoints([
      {
        gameDate: "2039-11-07",
        extractedAt: "2026-08-11T01:00:00.000Z",
        values: { professionalism: 12, ambition: 10 },
      },
      {
        gameDate: "2039-12-01",
        extractedAt: "2026-08-14T01:00:00.000Z",
        values: { professionalism: 14, ambition: 12 },
      },
    ]);
    expect(history).toHaveLength(2);
    expect(
      attrValueAndDelta(history, "general.professionalism", null, "allTime"),
    ).toEqual({ value: 14, delta: 2 });
    expect(
      attrValueAndDelta(history, "general.ambition", null, "allTime").delta,
    ).not.toBeNull();
  });

  it("Det/Lea route to CA; pack stays HA snapshots", () => {
    expect(isHaProgressAttrId("mental.determination")).toBe(false);
    expect(isHaProgressAttrId("mental.leadership")).toBe(false);
    expect(isHaProgressAttrId("general.professionalism")).toBe(true);
    expect(isHaProgressAttrId("physical.pace")).toBe(false);
    expect(isHaProgressAttrId("mental.decisions")).toBe(false);
    expect(
      splitEvolutionChartSelection([
        "mental.determination",
        "general.ambition",
      ]),
    ).toEqual({
      caIds: ["mental.determination"],
      haIds: ["general.ambition"],
    });
    expect(
      splitEvolutionChartSelection(["mental.determination", "physical.pace"]),
    ).toEqual({
      caIds: ["mental.determination", "physical.pace"],
      haIds: [],
    });
    expect(splitEvolutionChartSelection(["general.ambition"])).toEqual({
      caIds: [],
      haIds: ["general.ambition"],
    });
  });

  it("default Progress chips are pack keys only (not Det/Lea)", () => {
    const history = haSnapshotsToHistoryPoints([
      {
        gameDate: "2039-11-07",
        extractedAt: "2026-08-11T01:00:00.000Z",
        values: {
          professionalism: 16,
          pressure: 14,
          ambition: 10,
          temperament: 17,
          loyalty: 12,
          sportsmanship: 11,
          controversy: 8,
        },
        mental: { determination: 14, leadership: 8 },
      },
    ]);
    expect(defaultHaEvolutionAttrIds(history)).toEqual([
      "general.professionalism",
      "general.pressure",
      "general.ambition",
      "general.temperament",
      "general.loyalty",
      "general.sportsmanship",
      "general.controversy",
    ]);
  });
});
