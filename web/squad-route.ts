/**
 * Squad navigator hashes. Progress is club-wide (T048); no FT/II/U19 tabs.
 */

export const SQUAD_VIEW_MODES = [
  "firstTeam",
  "reserves",
  "under19s",
  "loans",
  "mentoring",
] as const;

export type SquadViewMode = (typeof SQUAD_VIEW_MODES)[number];

/** Per-unit detail: personalities grid vs attribute evolution. */
export type SquadUnitView = "personalities" | "attributes";

export function isSquadViewMode(
  value: string | null | undefined,
): value is SquadViewMode {
  return (
    value != null && (SQUAD_VIEW_MODES as readonly string[]).includes(value)
  );
}

export function isSquadUnitMode(
  mode: SquadViewMode,
): mode is "firstTeam" | "reserves" | "under19s" {
  return mode === "firstTeam" || mode === "reserves" || mode === "under19s";
}

export function rosterHashForView(
  mode: SquadViewMode = "firstTeam",
  unitView: SquadUnitView = "personalities",
): string {
  if (mode === "mentoring") return "#roster/mentoring";
  if (mode === "loans") return "#roster/loans";
  if (unitView === "attributes") return "#roster/progress";
  return "#roster";
}

export function parseRosterHash(raw: string): {
  squadView: SquadViewMode | null;
  unitView: SquadUnitView | null;
} {
  const parts = raw.replace(/^#/, "").split("/");
  const head = parts[0];
  const tab = parts[1];
  const detail = parts[2];
  if (head !== "roster" && head !== "squad") {
    return { squadView: null, unitView: null };
  }
  if (tab === "mentoring") {
    return { squadView: "mentoring", unitView: null };
  }
  if (tab === "loans") {
    return { squadView: "loans", unitView: null };
  }
  if (
    tab === "progress" ||
    tab === "attributes" ||
    detail === "attributes"
  ) {
    return { squadView: "firstTeam", unitView: "attributes" };
  }
  if (
    tab == null ||
    tab === "" ||
    tab === "personalities" ||
    tab === "first-team" ||
    tab === "firstTeam" ||
    tab === "reserves" ||
    tab === "reserve" ||
    tab === "ii" ||
    tab === "under19s" ||
    tab === "u19" ||
    tab === "under-19s" ||
    tab === "under19" ||
    tab === "penalties" ||
    tab === "scouting" ||
    tab === "scout"
  ) {
    return { squadView: "firstTeam", unitView: "personalities" };
  }
  if (isSquadViewMode(tab)) {
    return { squadView: tab, unitView: "personalities" };
  }
  return { squadView: null, unitView: null };
}
