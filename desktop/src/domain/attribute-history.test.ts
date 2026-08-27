import { describe, expect, it } from "vitest";
import {
  allTimeDeltasFromPoints,
  buildAttrTimeline,
  factualHistorySummary,
  fieldDeltas,
  movedFieldsBetween,
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

describe("allTimeDeltasFromPoints", () => {
  it("maps every tracked field to its all-time delta vs first point", () => {
    const points: AttrHistoryPoint[] = [
      { at: "2026-01-01", values: { CA: 100, Determination: 12 } },
      { at: "2026-01-02", values: { CA: 103, Determination: 14 } },
      { at: "2026-01-03", values: { CA: 102, Determination: 15 } },
    ];
    expect(allTimeDeltasFromPoints(points)).toEqual({ CA: 2, Determination: 3 });
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

describe("movedFieldsBetween", () => {
  it("lists signed deltas for fields that changed", () => {
    expect(
      movedFieldsBetween({ CA: 100, Determination: 12 }, { CA: 103, Determination: 12, Professionalism: 14 }),
    ).toEqual([
      { field: "Professionalism", from: null, to: 14, delta: 14 },
      { field: "CA", from: 100, to: 103, delta: 3 },
    ]);
  });

  it("returns empty when nothing moved", () => {
    expect(movedFieldsBetween({ CA: 100 }, { CA: 100 })).toEqual([]);
  });
});

describe("buildAttrTimeline", () => {
  it("returns newest-first rows with game date labels and moves vs prior", () => {
    const points: AttrHistoryPoint[] = [
      { at: "2026-01-01T10:00:00.000Z", gameDate: "July 2026", values: { CA: 100 } },
      { at: "2026-01-08T10:00:00.000Z", gameDate: "August 2026", values: { CA: 102 } },
    ];
    const rows = buildAttrTimeline(points);
    expect(rows).toHaveLength(2);
    expect(rows[0]!.label).toBe("August 2026");
    expect(rows[0]!.moves).toEqual([{ field: "CA", from: 100, to: 102, delta: 2 }]);
    expect(rows[1]!.isFirst).toBe(true);
    expect(rows[1]!.moves).toEqual([]);
  });
});

describe("factualHistorySummary", () => {
  it("states observation counts without Det/Pro mentoring advice", () => {
    const points: AttrHistoryPoint[] = [
      { at: "2026-01-01", values: { CA: 100, Determination: 10 } },
      { at: "2026-01-02", values: { CA: 104, Determination: 11 } },
    ];
    const summary = factualHistorySummary(points);
    expect(summary).toContain("2 observations");
    expect(summary).toContain("CA +4");
    expect(summary).toContain("2 fields moved last load");
    expect(summary?.toLowerCase()).not.toContain("mentor");
    expect(summary?.toLowerCase()).not.toContain("high-det");
  });
});
