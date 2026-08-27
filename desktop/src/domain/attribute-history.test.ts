import { describe, expect, it } from "vitest";
import {
  fieldDeltas,
  rankSquadMovers,
  recentDeltasFromPoints,
  type AttrHistoryPoint,
} from "./attribute-history";

describe("fieldDeltas", () => {
  const points: AttrHistoryPoint[] = [
    { at: "2026-01-01", values: { CA: 100, Passing: 10 } },
    { at: "2026-01-02", values: { CA: 102, Passing: 11 } },
    { at: "2026-01-03", values: { CA: 101, Passing: 11 } },
  ];

  it("computes recent vs previous change-point and all-time vs first", () => {
    expect(fieldDeltas(points, "CA")).toEqual({ recent: -1, allTime: 1, latest: 101 });
    expect(fieldDeltas(points, "Passing")).toEqual({ recent: 0, allTime: 1, latest: 11 });
  });

  it("returns null recent when only one point exists", () => {
    expect(fieldDeltas([points[0]!], "CA")).toEqual({ recent: null, allTime: null, latest: 100 });
  });
});

describe("recentDeltasFromPoints", () => {
  it("maps every tracked field to its recent delta", () => {
    const points: AttrHistoryPoint[] = [
      { at: "2026-01-01", values: { CA: 80, Determination: 12 } },
      { at: "2026-01-02", values: { CA: 83, Determination: 14 } },
    ];
    expect(recentDeltasFromPoints(points)).toEqual({ CA: 3, Determination: 2 });
  });
});

describe("rankSquadMovers", () => {
  const history: Record<string, AttrHistoryPoint[]> = {
    a: [
      { at: "2026-01-01", values: { CA: 100, Passing: 10 } },
      { at: "2026-01-02", values: { CA: 103, Passing: 12 } },
    ],
    b: [
      { at: "2026-01-01", values: { CA: 90 } },
      { at: "2026-01-02", values: { CA: 90 } },
    ],
    c: [{ at: "2026-01-01", values: { CA: 80 } }],
    d: [
      { at: "2026-01-01", values: { Determination: 12, Professionalism: 10 } },
      { at: "2026-01-02", values: { Determination: 14, Professionalism: 11 } },
    ],
  };

  it("returns only players with non-zero recent deltas, ranked by magnitude", () => {
    const ranked = rankSquadMovers(
      [{ id: "b" }, { id: "a" }, { id: "c" }, { id: "d" }],
      (id) => history[id] ?? [],
    );
    expect(ranked.map((row) => row.player.id)).toEqual(["a", "d"]);
    expect(ranked[0]!.magnitude).toBe(5);
    expect(ranked[0]!.changes.map((c) => c.field)).toEqual(["CA", "Passing"]);
    expect(ranked[1]!.changes.map((c) => c.field)).toEqual([
      "Determination",
      "Professionalism",
    ]);
  });

  it("returns empty when no second history point exists", () => {
    expect(rankSquadMovers([{ id: "c" }], (id) => history[id] ?? [])).toEqual([]);
  });

  it("respects limit", () => {
    expect(
      rankSquadMovers([{ id: "a" }, { id: "d" }], (id) => history[id] ?? [], 1),
    ).toHaveLength(1);
  });
});
