/**
 * Mentoring group persistence + prune safety (T026).
 *
 * Prevents extract refresh from wiping configured mentoring groups when roster
 * identity is incomplete or prune would delete every saved group.
 */

import type {
  MentoringHierarchyLabel,
  MentoringInfluenceLevel,
  MentoringInfluenceSeat,
} from "../src/index.ts";
import type { RosterPlayer } from "./roster-data.ts";

export const MENTORING_STACK_STORAGE_KEY = "fmt-mentoring-stack-v2";
export const MENTORING_STACK_STORAGE_KEY_LEGACY = "fmt-mentoring-stack-v1";

/** Minimum at-club headcount before prune trusts roster UIDs after extract refresh. */
export const MENTORING_ROSTER_PRUNE_MIN_FT = 3;

export type MentoringCaptaincyLabel = "captain" | "viceCaptain" | "none";
export type MentoringSocialGroupLabel =
  | "core"
  | "secondaryA"
  | "secondaryB"
  | "secondaryC"
  | "other";

export type MentoringDynamicsSnapshot = {
  age?: number;
  determination?: number;
  leadership?: number;
  haScore?: number;
  personality?: string;
};

export type MentoringDynamicsLabel = {
  captaincy: MentoringCaptaincyLabel | null;
  hierarchy: MentoringHierarchyLabel | null;
  socialGroup: MentoringSocialGroupLabel | null;
  labeledAt?: string;
  snapshot?: MentoringDynamicsSnapshot;
};

export type MentoringGroupRecord = {
  id: string;
  memberIds: string[];
  roles: Record<string, MentoringInfluenceSeat>;
  influenceEdges?: Record<string, MentoringInfluenceLevel>;
  /** Suggest finder why-lines. Omit for manual Add — do not invent. */
  reasons?: string[];
};

export type MentoringStackPersist = Record<
  string,
  {
    groups: MentoringGroupRecord[];
    dynamicsByPlayerId?: Record<string, MentoringDynamicsLabel>;
    rejectedGroupKeys?: string[];
  }
>;

export type MentoringStackSnapshot = {
  groups: MentoringGroupRecord[];
  dynamicsByPlayerId: Record<string, MentoringDynamicsLabel>;
  rejectedGroupKeys: string[];
};

export type MentoringPruneSkipReason = "incomplete_roster" | "would_wipe_all";

export type MentoringPruneDecision = {
  groups: MentoringGroupRecord[];
  changed: boolean;
  applied: boolean;
  skippedReason?: MentoringPruneSkipReason;
};

function emptyMentoringDynamicsLabel(): MentoringDynamicsLabel {
  return {
    captaincy: null,
    hierarchy: null,
    socialGroup: null,
  };
}

function isMentoringEdgeLevel(value: unknown): value is MentoringInfluenceLevel {
  return (
    value === "none" ||
    value === "light" ||
    value === "average" ||
    value === "significant"
  );
}

export function normalizeMentoringInfluenceEdges(
  raw: unknown,
): Record<string, MentoringInfluenceLevel> | undefined {
  if (!raw || typeof raw !== "object") return undefined;
  const out: Record<string, MentoringInfluenceLevel> = {};
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof key !== "string" || !key.includes(">")) continue;
    if (isMentoringEdgeLevel(value)) out[key] = value;
  }
  return Object.keys(out).length > 0 ? out : undefined;
}

export function normalizeMentoringGroupReasons(raw: unknown): string[] | undefined {
  if (!Array.isArray(raw)) return undefined;
  const bits = raw.filter(
    (row): row is string => typeof row === "string" && row.trim().length > 0,
  );
  return bits.length > 0 ? bits.slice(0, 4) : undefined;
}

/** Card/detail one-liner. Empty / missing → omit (manual Add has no fake why). */
export function mentoringGroupWhyLine(
  reasons: readonly string[] | undefined,
): string | null {
  if (!reasons?.length) return null;
  const bits = reasons.map((row) => row.trim()).filter(Boolean);
  if (bits.length === 0) return null;
  return bits.slice(0, 2).join(" · ");
}

function isMentoringCaptaincyLabel(value: unknown): value is MentoringCaptaincyLabel {
  return value === "captain" || value === "viceCaptain" || value === "none";
}

function isMentoringHierarchyLabel(value: unknown): value is MentoringHierarchyLabel {
  return (
    value === "teamLeader" ||
    value === "highlyInfluential" ||
    value === "influential" ||
    value === "other" ||
    value === "na"
  );
}

function isMentoringSocialGroupLabel(
  value: unknown,
): value is MentoringSocialGroupLabel {
  return (
    value === "core" ||
    value === "secondaryA" ||
    value === "secondaryB" ||
    value === "secondaryC" ||
    value === "other"
  );
}

export function normalizeMentoringDynamicsLabel(
  raw: unknown,
): MentoringDynamicsLabel | null {
  if (!raw || typeof raw !== "object") return null;
  const row = raw as Partial<MentoringDynamicsLabel>;
  const label = emptyMentoringDynamicsLabel();
  if (isMentoringCaptaincyLabel(row.captaincy)) label.captaincy = row.captaincy;
  if (isMentoringHierarchyLabel(row.hierarchy)) label.hierarchy = row.hierarchy;
  if (isMentoringSocialGroupLabel(row.socialGroup)) {
    label.socialGroup = row.socialGroup;
  }
  if (typeof row.labeledAt === "string") label.labeledAt = row.labeledAt;
  if (row.snapshot && typeof row.snapshot === "object") {
    label.snapshot = { ...row.snapshot };
  }
  return label;
}

export function normalizeMentoringGroupRecord(
  group: unknown,
): MentoringGroupRecord | null {
  if (!group || typeof group !== "object") return null;
  const row = group as MentoringGroupRecord;
  if (
    typeof row.id !== "string" ||
    !Array.isArray(row.memberIds) ||
    row.memberIds.length !== 3 ||
    !row.roles ||
    typeof row.roles !== "object"
  ) {
    return null;
  }
  const edges = normalizeMentoringInfluenceEdges(row.influenceEdges);
  const reasons = normalizeMentoringGroupReasons(row.reasons);
  return {
    id: row.id,
    memberIds: row.memberIds.map(String),
    roles: row.roles,
    ...(edges ? { influenceEdges: edges } : {}),
    ...(reasons ? { reasons } : {}),
  };
}

function snapshotFromPersistRow(
  row: MentoringStackPersist[string],
  groups: MentoringGroupRecord[],
): MentoringStackSnapshot {
  const dynamicsByPlayerId: Record<string, MentoringDynamicsLabel> = {};
  if (row.dynamicsByPlayerId && typeof row.dynamicsByPlayerId === "object") {
    for (const [id, value] of Object.entries(row.dynamicsByPlayerId)) {
      const label = normalizeMentoringDynamicsLabel(value);
      if (label) dynamicsByPlayerId[id] = label;
    }
  }
  const rejectedGroupKeys = Array.isArray(row.rejectedGroupKeys)
    ? row.rejectedGroupKeys.map(String)
    : [];
  return { groups, dynamicsByPlayerId, rejectedGroupKeys };
}

function migrateLegacyMentoringStack(
  store: MentoringStackPersist,
  persistKey: string,
): MentoringStackSnapshot | null {
  const prefix = `${persistKey}|`;
  let best: MentoringStackSnapshot | null = null;
  for (const [key, row] of Object.entries(store)) {
    if (!key.startsWith(prefix) || !row || !Array.isArray(row.groups)) continue;
    const groups = row.groups
      .map(normalizeMentoringGroupRecord)
      .filter((g): g is MentoringGroupRecord => g !== null);
    if (groups.length === 0) continue;
    const snapshot = snapshotFromPersistRow(row, groups);
    if (!best || snapshot.groups.length > best.groups.length) {
      best = snapshot;
    }
  }
  return best;
}

export function loadMentoringStackFromStore(
  store: MentoringStackPersist,
  persistKey: string,
): MentoringStackSnapshot {
  const empty: MentoringStackSnapshot = {
    groups: [],
    dynamicsByPlayerId: {},
    rejectedGroupKeys: [],
  };
  if (!persistKey) return empty;

  const direct = store[persistKey];
  let directSnapshot: MentoringStackSnapshot | null = null;
  if (direct && Array.isArray(direct.groups)) {
    const groups = direct.groups
      .map(normalizeMentoringGroupRecord)
      .filter((g): g is MentoringGroupRecord => g !== null);
    directSnapshot = snapshotFromPersistRow(direct, groups);
    if (groups.length > 0) return directSnapshot;
  }

  const legacy = migrateLegacyMentoringStack(store, persistKey);
  if (legacy) return legacy;

  return directSnapshot ?? empty;
}

export function loadMentoringStackFromStorage(
  persistKey: string,
  getItem: (key: string) => string | null,
): MentoringStackSnapshot {
  if (!persistKey) {
    return { groups: [], dynamicsByPlayerId: {}, rejectedGroupKeys: [] };
  }
  try {
    const raw =
      getItem(MENTORING_STACK_STORAGE_KEY) ??
      getItem(MENTORING_STACK_STORAGE_KEY_LEGACY);
    if (!raw) {
      return { groups: [], dynamicsByPlayerId: {}, rejectedGroupKeys: [] };
    }
    return loadMentoringStackFromStore(JSON.parse(raw) as MentoringStackPersist, persistKey);
  } catch {
    return { groups: [], dynamicsByPlayerId: {}, rejectedGroupKeys: [] };
  }
}

export function mentoringEdgesForMembers(
  edges: Record<string, MentoringInfluenceLevel> | undefined,
  memberIds: string[],
): Record<string, MentoringInfluenceLevel> | undefined {
  if (!edges) return undefined;
  const members = new Set(memberIds);
  const out: Record<string, MentoringInfluenceLevel> = {};
  for (const [key, level] of Object.entries(edges)) {
    const sep = key.indexOf(">");
    if (sep <= 0) continue;
    const from = key.slice(0, sep);
    const to = key.slice(sep + 1);
    if (!members.has(from) || !members.has(to)) continue;
    if (isMentoringEdgeLevel(level)) out[key] = level;
  }
  return Object.keys(out).length > 0 ? out : undefined;
}

export function buildMentoringPruneRosterIds(
  players: readonly RosterPlayer[],
): Set<string> {
  const loanedOutIds = new Set<string>();
  for (const p of players) {
    if (p.uid == null || !Number.isFinite(p.uid)) continue;
    if (p.loan?.status === "loanedOut") loanedOutIds.add(String(p.uid));
  }
  return new Set(
    players
      .filter((p) => p.uid != null && Number.isFinite(p.uid))
      .map((p) => String(p.uid))
      .filter((id) => !loanedOutIds.has(id)),
  );
}

export function isMentoringRosterTrustworthyForPrune(
  clubPlayers: readonly RosterPlayer[],
  atClubMentoringPool: readonly RosterPlayer[],
): boolean {
  if (clubPlayers.length === 0) return false;
  if (atClubMentoringPool.length === 0) return false;
  if (atClubMentoringPool.length < MENTORING_ROSTER_PRUNE_MIN_FT) return false;
  return true;
}

export function pruneMentoringGroupRecords(
  groups: readonly MentoringGroupRecord[],
  rosterIds: ReadonlySet<string>,
): { groups: MentoringGroupRecord[]; changed: boolean } {
  const seenPlayers = new Set<string>();
  const nextGroups: MentoringGroupRecord[] = [];

  for (const group of groups) {
    const memberIds = group.memberIds.filter((id) => rosterIds.has(id));
    if (memberIds.length !== 3) continue;
    if (memberIds.some((id) => seenPlayers.has(id))) continue;
    for (const id of memberIds) seenPlayers.add(id);
    const influenceEdges = mentoringEdgesForMembers(group.influenceEdges, memberIds);
    const reasons = normalizeMentoringGroupReasons(group.reasons);
    nextGroups.push({
      id: group.id,
      memberIds,
      roles: Object.fromEntries(
        Object.entries(group.roles).filter(([id]) => memberIds.includes(id)),
      ),
      ...(influenceEdges ? { influenceEdges } : {}),
      ...(reasons ? { reasons } : {}),
    });
  }

  const changed =
    nextGroups.length !== groups.length ||
    nextGroups.some((group, index) => {
      const prev = groups[index];
      return (
        !prev ||
        prev.id !== group.id ||
        prev.memberIds.join("|") !== group.memberIds.join("|")
      );
    });

  return { groups: nextGroups, changed };
}

export function decideMentoringPrune(
  currentGroups: readonly MentoringGroupRecord[],
  rosterIds: ReadonlySet<string>,
  rosterTrustworthy: boolean,
): MentoringPruneDecision {
  if (!rosterTrustworthy || rosterIds.size === 0) {
    return {
      groups: [...currentGroups],
      changed: false,
      applied: false,
      skippedReason: "incomplete_roster",
    };
  }

  const { groups: nextGroups, changed } = pruneMentoringGroupRecords(
    currentGroups,
    rosterIds,
  );

  if (nextGroups.length === 0 && currentGroups.length > 0) {
    return {
      groups: [...currentGroups],
      changed: false,
      applied: false,
      skippedReason: "would_wipe_all",
    };
  }

  return {
    groups: nextGroups,
    changed,
    applied: changed,
  };
}

export function canPersistMentoringGroupsToStore(
  groups: readonly MentoringGroupRecord[],
  store: MentoringStackPersist,
  persistKey: string,
): boolean {
  if (groups.length > 0) return true;
  const existing = store[persistKey]?.groups;
  if (!existing || !Array.isArray(existing)) return true;
  const normalized = existing
    .map(normalizeMentoringGroupRecord)
    .filter((g): g is MentoringGroupRecord => g !== null);
  return normalized.length === 0;
}

export function sampleMentoringGroup(
  id: string,
  memberIds: [string, string, string],
): MentoringGroupRecord {
  const [high, mid, low] = memberIds;
  return {
    id,
    memberIds: [...memberIds],
    roles: {
      [high]: "high",
      [mid]: "mid",
      [low]: "low",
    },
  };
}
