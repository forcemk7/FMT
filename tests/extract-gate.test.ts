import { describe, expect, it } from "vitest";
import { createExtractGate } from "../shared/save/extract-gate.ts";

describe("createExtractGate (T072)", () => {
  it("runs exclusive fns one at a time", async () => {
    const runExclusive = createExtractGate();
    let overlap = 0;
    let maxOverlap = 0;
    const job = async (ms: number) => {
      overlap += 1;
      maxOverlap = Math.max(maxOverlap, overlap);
      await new Promise((r) => setTimeout(r, ms));
      overlap -= 1;
      return ms;
    };
    const [a, b, c] = await Promise.all([
      runExclusive(() => job(40)),
      runExclusive(() => job(40)),
      runExclusive(() => job(40)),
    ]);
    expect([a, b, c]).toEqual([40, 40, 40]);
    expect(maxOverlap).toBe(1);
  });

  it("starts the next job after a failure", async () => {
    const runExclusive = createExtractGate();
    await expect(
      runExclusive(async () => {
        throw new Error("boom");
      }),
    ).rejects.toThrow("boom");
    await expect(runExclusive(async () => "ok")).resolves.toBe("ok");
  });
});
