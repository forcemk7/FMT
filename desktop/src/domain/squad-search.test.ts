import { describe, expect, it } from "vitest";
import { foldSearchText, playerMatchesSquadSearch } from "./squad-search";

describe("foldSearchText", () => {
  it("strips combining marks and lowercases", () => {
    expect(foldSearchText("Ilan Kramarić")).toBe("ilan kramaric");
    expect(foldSearchText("José")).toBe("jose");
    expect(foldSearchText("Łukasz")).toBe("łukasz");
  });
});

describe("playerMatchesSquadSearch", () => {
  it("matches ASCII query against diacritic name", () => {
    expect(playerMatchesSquadSearch("Ilan Kramarić", "kramaric")).toBe(true);
    expect(playerMatchesSquadSearch("Ilan Kramarić", "ilan kramaric")).toBe(true);
    expect(playerMatchesSquadSearch("Ilan Kramarić", "KRAM")).toBe(true);
  });

  it("still supports plain substring", () => {
    expect(playerMatchesSquadSearch("John Smith", "smi")).toBe(true);
    expect(playerMatchesSquadSearch("John Smith", "jones")).toBe(false);
  });

  it("rejects empty / whitespace query", () => {
    expect(playerMatchesSquadSearch("Ilan Kramarić", "")).toBe(false);
    expect(playerMatchesSquadSearch("Ilan Kramarić", "   ")).toBe(false);
  });
});
