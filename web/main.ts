import {
  ATTRIBUTE_DESCRIPTIONS,
  ATTRIBUTE_LABELS,
  HAS_ATTRIBUTES,
  PERSONALITY_ATTRIBUTES,
  PERSONALITY_ATTRIBUTE_ABBR,
  PERSONALITY_ATTRIBUTE_LABELS,
  VISIBLE_ATTRIBUTES,
  CHECKER_TABLE_ATTRIBUTES,
  FULL_RANGE,
  attributeTone,
  estimatePlayer,
  findMediaHandling,
  findPersonality,
  formatMediaHandlingLabel,
  hiddenQualityScore,
  hiddenQualityTone,
  isPersonalityMediaCompatible,
  isUnmodeledHiddenAttribute,
  loadCatalog,
  parseMediaHandlingInput,
  personalityMediaContradictions,
  rankPersonalityMediaCombos,
  rankPersonalityMediaCombosUnified,
  defaultMentoringUnitRoles,
  evaluateMentoringUnit,
  findInfluenceSafeMentoringGroups,
  MENTORING_DISPLAY_ORDER,
  HA_QUALITY_WEIGHTS,
  HA_VISIBLE_QUALITY_WEIGHTS,
  HIDDEN_QUALITY_GOOD_FLOOR,
  HIDDEN_QUALITY_BAD_CEILING,
  invertControversy,
  formatHaQualityWeightsTip,
  haQualityWeightSum,
  resolvePoorHasCeiling,
  toEstimate,
  comboFeasibleForAttrs,
  type AttributeEstimates,
  type HaVisibleKnown,
  type CaseMode,
  type ComboRankEntry,
  type EstimateResult,
  type FieldViolation,
  type HasAttribute,
  type HiddenAttribute,
  type VisibleAttribute,
  type TrackedAttribute,
  type MediaHandlingDefinition,
  type MentoringCandidate,
  type MentoringHierarchyLabel,
  type MentoringInfluenceLevel,
  type MentoringInfluenceSafeGroup,
  type MentoringInfluenceSeat,
  type MentoringSubject,
  type MentoringUnitEvaluation,
  type MentoringUnitMember,
  type PersonalityDefinition,
  type RankPopulationMode,
} from "../src/index.ts";
import {
  emptyHistoryStore,
  findPlayer,
  findSave,
  normalizeHistoryStore,
  playerCount,
  type GameSave,
  type HistorySignals,
  type HistoryStore,
  type PlayerEntry,
  type PlayerLabels,
} from "../shared/history-store.ts";
import {
  CUSTOM_DATABASE_VALUE,
  FM_DATABASE_VERSIONS,
  FM_GAME_VERSIONS,
} from "./fm-meta.ts";
import { probeSaveFile, type SaveMetaProbe } from "./save-meta.ts";
import {
  normalizeRosterPlayer,
  rosterPersonalitySignals,
  rosterPlayerAge,
  type LegacyRosterPlayer,
  type PersonalitySignals,
  type RosterPlayer,
} from "./roster-data.ts";
import { loansByUnit } from "./loans-roster.ts";
import {
  extractTrustHoles,
  formatExtractTrustStatus,
  isMentoringCompleteEnough,
  mentoringSuggestPool,
  playerExtractTrust,
  rosterResolvedName,
  summarizeExtractTrust,
} from "./extract-trust.ts";
import {
  deleteRoster,
  listRosterSaveNames,
  loadRosterStore,
  setActiveRoster,
  shouldRefreshRosterFromDisk,
  tipOnlyAttributeHistory,
  upsertRoster,
  type RosterStore,
  type StoredFavouredClub,
  type StoredReservesSquad,
  type StoredU19Squad,
} from "./roster-store.ts";
import {
  allSelectableEvolutionIds,
  attrValueAndDelta,
  buildEvolutionSeries,
  colorForActiveEvolutionAttr,
  defaultEvolutionAttrIds,
  evolutionCategoriesWithPersonality,
  filterAttributeHistory,
  formatAttrDelta,
  hitTestEvolutionPoint,
  historyPointValue,
  labelForEvolutionAttr,
  liveAttrValue,
  renderEvolutionChartSvg,
  type EvolutionAttrId,
  type EvolutionHoverPoint,
} from "./attribute-evolution.ts";
import {
  backfillHaHistoryFromRosterStore,
  getPlayerHaHistory,
  haSnapshotsToHistoryPoints,
  loadHaHistoryStore,
  mergeHaHistoryFromRoster,
  type HaHistoryStore,
} from "./ha-history-store.ts";

const catalog = loadCatalog();
const mediaStyles = catalog.mediaHandling.map((m) => m.id);

const shellEl = document.querySelector<HTMLElement>(".shell")!;
const historyToggleEl = document.querySelector<HTMLButtonElement>("#history-toggle")!;
const historyListEl = document.querySelector<HTMLUListElement>("#history-list")!;
const historyEmptyEl = document.querySelector<HTMLElement>("#history-empty")!;
const historyHeadingEl = document.querySelector<HTMLElement>("#history-heading")!;
const historyBackEl = document.querySelector<HTMLButtonElement>("#history-back")!;
const historyNewEl = document.querySelector<HTMLButtonElement>("#history-new")!;
const historyNewPlayerEl = document.querySelector<HTMLButtonElement>(
  "#history-new-player",
)!;
const historyPlayerSortEl = document.querySelector<HTMLElement>(
  "#history-player-sort",
)!;
const historySortByEl = document.querySelector<HTMLSelectElement>(
  "#history-sort-by",
)!;
const historySortDirEl = document.querySelector<HTMLButtonElement>(
  "#history-sort-dir",
)!;
const historyDeleteEl = document.querySelector<HTMLButtonElement>("#history-delete")!;
const checkerDialogEl = document.querySelector<HTMLDialogElement>("#checker-dialog")!;
const checkerEl = document.querySelector<HTMLElement>("#checker")!;
const checkerCloseEl = document.querySelector<HTMLButtonElement>("#checker-close")!;
const probeModeEl = document.querySelector<HTMLElement>(".probe-mode")!;
const probeTitleFocusEl = document.querySelector<HTMLElement>("#probe-title-focus")!;
const probeLedeEl = document.querySelector<HTMLElement>("#probe-lede")!;
const compareEl = document.querySelector<HTMLElement>("#compare")!;
const rankEl = document.querySelector<HTMLElement>("#rank")!;
const rosterEl = document.querySelector<HTMLElement>("#roster")!;
const rosterSaveControllerEl = document.querySelector<HTMLElement>(
  "#roster-save-controller",
)!;
const rosterClubLineEl = document.querySelector<HTMLElement>("#roster-club-line")!;
const rosterTablePanelEl = document.querySelector<HTMLElement>(".roster-table-panel")!;
const rosterBodyEl = document.querySelector<HTMLElement>("#roster-body")!;
const rosterStatusEl = document.querySelector<HTMLElement>("#roster-status")!;
const rosterUploadEl = document.querySelector<HTMLInputElement>("#roster-upload")!;
const rosterUploadBtnEl = document.querySelector<HTMLButtonElement>("#roster-upload-btn")!;
const rosterEmptyEl = document.querySelector<HTMLElement>("#roster-empty")!;
const squadViewToolbarStartEl = document.querySelector<HTMLElement>(
  ".squad-view-toolbar-start",
)!;
const squadViewTabsEl = document.querySelector<HTMLElement>(".squad-view-tabs")!;
const squadPersonalitiesPaneEl = document.querySelector<HTMLElement>(
  "#squad-personalities-pane",
)!;
const squadMentoringPaneEl = document.querySelector<HTMLElement>(
  "#squad-mentoring-pane",
)!;
const squadViewFirstTeamEl = document.querySelector<HTMLButtonElement>(
  "#squad-view-first-team",
)!;
const squadViewReservesEl = document.querySelector<HTMLButtonElement>(
  "#squad-view-reserves",
)!;
const squadViewUnder19sEl = document.querySelector<HTMLButtonElement>(
  "#squad-view-under19s",
)!;
const squadViewMentoringEl = document.querySelector<HTMLButtonElement>(
  "#squad-view-mentoring",
)!;
const squadViewLoansEl = document.querySelector<HTMLButtonElement>(
  "#squad-view-loans",
)!;
const squadLoansPaneEl = document.querySelector<HTMLElement>(
  "#squad-loans-pane",
)!;
const squadLoansEmptyEl = document.querySelector<HTMLElement>(
  "#squad-loans-empty",
)!;
const squadEvolutionEl = document.querySelector<HTMLElement>("#squad-evolution")!;
const squadEvolutionPlayerPickerEl = document.querySelector<HTMLElement>(
  "#squad-evolution-player-picker",
)!;
const squadEvolutionPlayerTriggerEl = document.querySelector<HTMLButtonElement>(
  "#squad-evolution-player-trigger",
)!;
const squadEvolutionPlayerFaceWrapEl = document.querySelector<HTMLElement>(
  "#squad-evolution-player-trigger .squad-evo-player-face-wrap",
)!;
const squadEvolutionPlayerFaceEl = document.querySelector<HTMLImageElement>(
  "#squad-evolution-player-face",
)!;
const squadEvolutionPlayerLabelEl = document.querySelector<HTMLElement>(
  "#squad-evolution-player-label",
)!;
const squadEvolutionPlayerListEl = document.querySelector<HTMLUListElement>(
  "#squad-evolution-player-list",
)!;
const squadEvolutionSubEl = document.querySelector<HTMLElement>(
  "#squad-evolution-sub",
)!;
const squadEvolutionChartEl = document.querySelector<HTMLElement>(
  "#squad-evolution-chart",
)!;
const squadEvolutionTogglesEl = document.querySelector<HTMLElement>(
  "#squad-evolution-toggles",
)!;
const squadEvoVisibilityToolsEl = document.querySelector<HTMLElement>(
  "#squad-evo-visibility-tools",
)!;
const squadEvoShowAllEl = document.querySelector<HTMLButtonElement>(
  "#squad-evo-show-all",
)!;
const squadEvoHideAllEl = document.querySelector<HTMLButtonElement>(
  "#squad-evo-hide-all",
)!;
const rosterSavesBtnEl = document.querySelector<HTMLButtonElement>("#roster-saves-btn")!;
const rosterSavesMenuEl = document.querySelector<HTMLElement>("#roster-saves-menu")!;
const rosterSavesCountEl = document.querySelector<HTMLElement>("#roster-saves-count")!;
const rosterSavesListEl = document.querySelector<HTMLElement>("#roster-saves-list")!;
const rosterSavesEmptyEl = document.querySelector<HTMLElement>("#roster-saves-empty")!;
const toolNavEl = document.querySelector<HTMLElement>("#tool-nav")!;
const appBrandEl = document.querySelector<HTMLButtonElement>(".app-brand")!;
const rankerPodiumEl = document.querySelector<HTMLElement>("#ranker-podium")!;
const rankerListEl = document.querySelector<HTMLElement>("#ranker-list")!;
const rankerSearchEl = document.querySelector<HTMLInputElement>("#ranker-search")!;
const rankerFindCountEl = document.querySelector<HTMLElement>("#ranker-find-count")!;
const rankerFindPrevEl = document.querySelector<HTMLButtonElement>("#ranker-find-prev")!;
const rankerFindNextEl = document.querySelector<HTMLButtonElement>("#ranker-find-next")!;

type AppTool = "rank" | "roster";
type ProbeMode = "single" | "compare";

const TOOL_STORAGE_KEY = "fmt.activeTool";
/** Persists squad history in the browser when the Vite disk API is unavailable (e.g. GitHub Pages). */
const HISTORY_STORAGE_KEY = "fmt.history.v2";
/** Dev server has /api/history; static hosts (Pages, vite preview) do not. */
const useHistoryApi = import.meta.env.DEV;
/** Dev server has /api/roster; static hosts do not. */
const useRosterApi = import.meta.env.DEV;

let rosterStore: RosterStore = loadRosterStore();
let haHistoryStore: HaHistoryStore = backfillHaHistoryFromRosterStore(
  loadHaHistoryStore(),
  rosterStore,
);
let firstTeamPlayers: RosterPlayer[] = [];
let reservesPlayers: RosterPlayer[] = [];
let under19sPlayers: RosterPlayer[] = [];
/** Active unit players — kept in sync for renderRoster / evolution helpers. */
let rosterPlayers: RosterPlayer[] = [];
let rosterMeta: {
  source: "empty" | "save";
  saveName?: string;
  clubId?: number;
  teamId?: number;
  clubName?: string;
  clubNameShort?: string;
  elapsedMs?: number;
  extractedAt?: string;
  dateCreated?: string | null;
  lastSaved?: string | null;
  gameDate?: string | null;
  error?: string;
} = { source: "empty" };
/** Pending overwrite slot (set via Saves → Update); next upload replaces it. */
let rosterAmendTarget: string | null = null;
/** True while a disk/upload extract is running. */
let rosterRefreshInFlight = false;
/** True when the in-flight extract is non-blocking auto-sync. */
let rosterBackgroundSync = false;
/** Waiters for manual upload/update while a refresh is in flight. */
let rosterRefreshIdleWaiters: Array<() => void> = [];
/** Coalesce another auto-sync if the save changes again mid-extract. */
let rosterBackgroundSyncQueued = false;
let rosterStatusClearTimer: ReturnType<typeof setTimeout> | null = null;
let saveAutoSyncStarted = false;
let savePollTimer: ReturnType<typeof setInterval> | null = null;
let saveEventSource: EventSource | null = null;
/** True while the native Career Save file dialog is open. */
let rosterFileDialogOpen = false;
let rosterSavesMenuOpen = false;
/** 5×5 matrix: one page holds up to 25 ranked players. */
/** Top Squad tabs: three identical squad pages + Loans + club-wide Mentoring. */
type SquadViewMode =
  | "firstTeam"
  | "reserves"
  | "under19s"
  | "loans"
  | "mentoring";
const SQUAD_VIEW_MODES: readonly SquadViewMode[] = [
  "firstTeam",
  "reserves",
  "under19s",
  "loans",
  "mentoring",
];
/** Per-unit detail: personalities grid vs attribute evolution. */
type SquadUnitView = "personalities" | "attributes";
function isSquadViewMode(value: string | null | undefined): value is SquadViewMode {
  return (
    value != null &&
    (SQUAD_VIEW_MODES as readonly string[]).includes(value)
  );
}
function isSquadUnitMode(
  mode: SquadViewMode,
): mode is "firstTeam" | "reserves" | "under19s" {
  return mode === "firstTeam" || mode === "reserves" || mode === "under19s";
}
let squadViewMode: SquadViewMode = "firstTeam";
let squadUnitView: SquadUnitView = "personalities";
/** Deep-link / reload restore for Squad tabs (`#roster/mentoring`). */
let pendingSquadViewMode: SquadViewMode | null = null;
let pendingSquadUnitView: SquadUnitView | null = null;
let squadEvolutionUid: number | null = null;
let squadEvolutionAttrs: EvolutionAttrId[] = [];
/** Overrides role-default / custom pill selection when active. */
let squadEvolutionAttrOverride: "default" | "all" | "none" = "default";
let squadEvolutionHover: EvolutionHoverPoint | null = null;

type MentoringGroupRecord = {
  id: string;
  memberIds: string[];
  roles: Record<string, MentoringInfluenceSeat>;
  /**
   * Directed mentoring-triangle influence from FM (A→B).
   * Key: `${fromId}>${toId}` → none | light | average | significant.
   */
  influenceEdges?: Record<string, MentoringInfluenceLevel>;
};

/** User-tagged Dynamics labels from FM (compatible — not inferred). */
type MentoringCaptaincyLabel = "captain" | "viceCaptain" | "none";
type MentoringSocialGroupLabel =
  | "core"
  | "secondaryA"
  | "secondaryB"
  | "secondaryC"
  | "other";

type MentoringDynamicsSnapshot = {
  age?: number;
  determination?: number;
  leadership?: number;
  haScore?: number;
  personality?: string;
};

type MentoringDynamicsLabel = {
  captaincy: MentoringCaptaincyLabel | null;
  hierarchy: MentoringHierarchyLabel | null;
  socialGroup: MentoringSocialGroupLabel | null;
  labeledAt?: string;
  snapshot?: MentoringDynamicsSnapshot;
};

/** Per-peer influence draft while editing a group member. */
type MentoringPeerInfluenceDraft = {
  on: MentoringInfluenceLevel | null;
  from: MentoringInfluenceLevel | null;
};

type MentoringDynamicsDraft = MentoringDynamicsLabel & {
  /** Peer id → on/from levels for the open group. */
  influenceByPeerId: Record<string, MentoringPeerInfluenceDraft>;
};

type MentoringCachedSuggestion = MentoringGroupRecord & {
  score: number;
  path: string;
  /** Stable key for dedupe / cycling. */
  key: string;
};

type MentoringCache = {
  /** Stable save identity used for localStorage (save name). */
  persistKey: string;
  /** Session fingerprint — rebuild candidates/suggestions when this changes. */
  sessionKey: string;
  groups: MentoringGroupRecord[];
  /** Player Dynamics labels keyed by player id (uid string). */
  dynamicsByPlayerId: Record<string, MentoringDynamicsLabel>;
  /** Built once per session key — avoid rematching combos on every render. */
  candidates: MentoringCandidate[] | null;
  suggestions: MentoringCachedSuggestion[];
  suggestionCursor: number;
  suggestionsStatus: "idle" | "loading" | "ready";
  generation: number;
};

let mentoringCache: MentoringCache = {
  persistKey: "",
  sessionKey: "",
  groups: [],
  dynamicsByPlayerId: {},
  candidates: null,
  suggestions: [],
  suggestionCursor: 0,
  suggestionsStatus: "idle",
  generation: 0,
};
/** Bump when group-edge scoring changes so suggestion caches refresh (not group storage). */
const MENTORING_LOGIC_REV = 11;
const MENTORING_STACK_STORAGE_KEY = "fmt-mentoring-stack-v2";
const MENTORING_STACK_STORAGE_KEY_LEGACY = "fmt-mentoring-stack-v1";
/** Skip DOM rebuild when groups/dynamics unchanged (avoids face skeleton flicker). */
let mentoringRenderFingerprint = "";

type MentoringPickerState = {
  /** null = creating a new group */
  groupId: string | null;
  selectedIds: string[];
  /** Avoid rebuilding the whole table on every toggle. */
  builtRosterKey: string | null;
  /** Suggestions already cycled this picker session. */
  shownSuggestionKeys: Set<string>;
};

let mentoringPicker: MentoringPickerState | null = null;
let mentoringDetailGroupId: string | null = null;
let mentoringDynamicsPlayerId: string | null = null;
let mentoringDynamicsGroupId: string | null = null;
let mentoringDynamicsDraft: MentoringDynamicsDraft | null = null;

type ScoutPlayerRow = {
  uid: number;
  name?: string | null;
  affinity: number;
  ca?: number | null;
  pa?: number | null;
};

type ScoutExtractState = {
  saveName?: string;
  clubId?: number;
  clubName?: string | null;
  clubNameShort?: string | null;
  players: ScoutPlayerRow[];
  hitCount?: number;
  elapsedMs?: number;
  error?: string | null;
  /** True when this save has never been scout-scanned (legacy Squad extracts). */
  missing?: boolean;
};

let scoutState: ScoutExtractState = { players: [], missing: true };

function activeSquadPlayers(): RosterPlayer[] {
  if (squadViewMode === "reserves") return reservesPlayers;
  if (squadViewMode === "under19s") return under19sPlayers;
  return firstTeamPlayers;
}

function syncActiveSquadPlayers(): void {
  rosterPlayers = activeSquadPlayers();
}

/**
 * Mentoring pool = managed-club employees at club only.
 * Employment proof is extract FT list membership (club-object→7f02 join);
 * loaned-out employees stay on FT `players[]` but never seat here (T007/T009).
 */
function firstTeamMentoringPlayers(): RosterPlayer[] {
  const byUid = new Map<number, RosterPlayer>();
  for (const p of firstTeamPlayers) {
    if (p.uid == null || !Number.isFinite(p.uid)) continue;
    // Loaned-out players stay on the squad list but are unavailable in-game.
    if (p.loan?.status === "loanedOut") continue;
    byUid.set(p.uid, p);
  }
  return [...byUid.values()];
}

/** Club-wide roster for empty checks / uid lookup (FT + Reserves + U19). */
function clubAllPlayers(): RosterPlayer[] {
  const byUid = new Map<number, RosterPlayer>();
  for (const p of [
    ...firstTeamPlayers,
    ...reservesPlayers,
    ...under19sPlayers,
  ]) {
    if (p.uid == null || !Number.isFinite(p.uid)) continue;
    byUid.set(p.uid, p);
  }
  return [...byUid.values()];
}

function playerLoanBadgeClubId(player: RosterPlayer): number | null {
  const loan = player.loan;
  if (!loan) return null;
  if (loan.status === "loanedOut") {
    return loan.loanClubId != null && Number.isFinite(loan.loanClubId)
      ? loan.loanClubId
      : null;
  }
  if (loan.status === "loanedIn") {
    return loan.parentClubId != null && Number.isFinite(loan.parentClubId)
      ? loan.parentClubId
      : null;
  }
  return null;
}

function playerLoanBadgeLabel(player: RosterPlayer): string | null {
  const loan = player.loan;
  if (!loan) return null;
  if (loan.status === "loanedOut") {
    return loan.loanClubName?.trim() || "Loan club";
  }
  if (loan.status === "loanedIn") {
    return loan.parentClubName?.trim() || "Parent club";
  }
  return null;
}

function clubPlayerCount(): number {
  return clubAllPlayers().length;
}

function findRosterPlayer(uid: number): RosterPlayer | undefined {
  return (
    rosterPlayers.find((p) => p.uid === uid) ??
    clubAllPlayers().find((p) => p.uid === uid)
  );
}

function rosterHashForView(
  mode: SquadViewMode = squadViewMode,
  unitView: SquadUnitView = squadUnitView,
): string {
  if (mode === "mentoring") return "#roster/mentoring";
  if (mode === "loans") return "#roster/loans";
  const unit =
    mode === "firstTeam" ? "first-team" : mode === "under19s" ? "under19s" : mode;
  if (mode === "firstTeam" && unitView === "personalities") return "#roster";
  if (unitView === "attributes") return `#roster/${unit}/attributes`;
  return `#roster/${unit}`;
}

function syncRosterViewHash(
  mode: SquadViewMode = squadViewMode,
  unitView: SquadUnitView = squadUnitView,
) {
  // Defer: setSquadViewMode may run during early roster bootstrap before
  // `activeTool` is initialized (TDZ on module load).
  queueMicrotask(() => {
    if (squadViewMode !== mode || squadUnitView !== unitView) return;
    // `activeTool` is declared later in this module — skip until init finishes.
    let tool: AppTool | undefined;
    try {
      tool = activeTool;
    } catch {
      return;
    }
    if (tool !== "roster") return;
    const nextHash = rosterHashForView(mode, unitView);
    if (window.location.hash !== nextHash) {
      window.history.replaceState(
        null,
        "",
        `${window.location.pathname}${window.location.search}${nextHash}`,
      );
    }
  });
}

function setSquadUnitView(view: SquadUnitView) {
  squadUnitView = view;
  if (!isSquadUnitMode(squadViewMode)) {
    squadViewMode = "firstTeam";
  }
  setSquadViewMode(squadViewMode);
}

function setSquadViewMode(mode: SquadViewMode) {
  squadViewMode = mode;
  const isUnit = isSquadUnitMode(mode);
  const isMentoring = mode === "mentoring";
  const isLoans = mode === "loans";
  const isAttrs = isUnit && squadUnitView === "attributes";
  const isPersonalities = isUnit && squadUnitView === "personalities";

  syncActiveSquadPlayers();

  squadViewFirstTeamEl.classList.toggle("is-active", mode === "firstTeam");
  squadViewReservesEl.classList.toggle("is-active", mode === "reserves");
  squadViewUnder19sEl.classList.toggle("is-active", mode === "under19s");
  squadViewLoansEl.classList.toggle("is-active", isLoans);
  squadViewMentoringEl.classList.toggle("is-active", isMentoring);
  squadViewFirstTeamEl.setAttribute("aria-selected", String(mode === "firstTeam"));
  squadViewReservesEl.setAttribute("aria-selected", String(mode === "reserves"));
  squadViewUnder19sEl.setAttribute("aria-selected", String(mode === "under19s"));
  squadViewLoansEl.setAttribute("aria-selected", String(isLoans));
  squadViewMentoringEl.setAttribute("aria-selected", String(isMentoring));

  squadPersonalitiesPaneEl.hidden = !isPersonalities;
  squadEvolutionEl.hidden = !isAttrs;
  squadLoansPaneEl.hidden = !isLoans;
  squadMentoringPaneEl.hidden = !isMentoring;

  const panel = document.querySelector(".squad-grid-panel");
  panel?.classList.remove(
    "is-attributes",
    "is-mentoring",
    "is-loans",
    "is-reserves",
    "is-under19s",
    "is-first-team",
  );
  if (isAttrs) panel?.classList.add("is-attributes");
  if (isMentoring) panel?.classList.add("is-mentoring");
  if (isLoans) panel?.classList.add("is-loans");
  if (mode === "reserves") panel?.classList.add("is-reserves");
  if (mode === "under19s") panel?.classList.add("is-under19s");
  if (mode === "firstTeam") panel?.classList.add("is-first-team");

  syncRosterViewHash(mode, squadUnitView);

  if (isAttrs) {
    squadEvolutionHover = null;
    populateSquadEvolutionPlayers();
    if (
      squadEvolutionUid == null ||
      !rosterPlayers.some((p) => p.uid === squadEvolutionUid)
    ) {
      const first =
        rosterPlayers.find((p) => (p.attributeHistory?.length ?? 0) > 0) ??
        rosterPlayers[0];
      if (first) selectSquadEvolutionPlayer(first.uid);
      else {
        clearSquadEvolution();
        renderSquadEvolution();
      }
    } else {
      renderSquadEvolution();
    }
  } else if (isMentoring) {
    squadEvolutionHover = null;
    try {
      renderMentoringPage();
    } catch (err) {
      console.error("Mentoring page failed to render", err);
      try {
        mentoringCardsEl.replaceChildren();
        mentoringEmptyEl.hidden = false;
        mentoringEmptyEl.textContent = "Mentoring failed to load";
        mentoringStatusEl.textContent = "Mentoring failed to load";
      } catch {
        /* still initializing */
      }
    }
  } else if (isLoans) {
    squadEvolutionHover = null;
    renderLoansPage();
  } else {
    squadEvolutionHover = null;
    renderRoster();
  }
}

function closeSquadEvolutionPlayerList() {
  squadEvolutionPlayerListEl.hidden = true;
  squadEvolutionPlayerTriggerEl.setAttribute("aria-expanded", "false");
}

function openSquadEvolutionPlayerList() {
  squadEvolutionPlayerListEl.hidden = false;
  squadEvolutionPlayerTriggerEl.setAttribute("aria-expanded", "true");
  const selected = squadEvolutionPlayerListEl.querySelector<HTMLElement>(
    '[aria-selected="true"]',
  );
  selected?.focus();
}

function setSquadEvolutionPlayerTrigger(player: RosterPlayer | null) {
  if (!player) {
    squadEvolutionPlayerLabelEl.textContent = "Select player";
    squadEvolutionPlayerFaceEl.removeAttribute("src");
    squadEvolutionPlayerFaceEl.classList.remove("is-ready", "is-missing");
    squadEvolutionPlayerFaceWrapEl.classList.add("has-no-face");
    return;
  }
  const n = player.attributeHistory?.length ?? 0;
  squadEvolutionPlayerLabelEl.textContent =
    n > 0 ? `${player.name} (${n})` : player.name || String(player.uid);
  squadEvolutionPlayerFaceWrapEl.classList.add("has-no-face");
  squadEvolutionPlayerFaceEl.classList.remove("is-ready", "is-missing");
  bindPlayerFace(squadEvolutionPlayerFaceEl, player.uid, {
    onReady: () => squadEvolutionPlayerFaceWrapEl.classList.remove("has-no-face"),
    onMissing: () => squadEvolutionPlayerFaceWrapEl.classList.add("has-no-face"),
  });
}

function populateSquadEvolutionPlayers() {
  const previous = squadEvolutionUid;
  squadEvolutionPlayerListEl.replaceChildren();
  const sorted = [...rosterPlayers].sort((a, b) =>
    (a.name || "").localeCompare(b.name || "", undefined, { sensitivity: "base" }),
  );
  for (const player of sorted) {
    const li = document.createElement("li");
    li.setAttribute("role", "none");

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "squad-evo-player-option";
    btn.setAttribute("role", "option");
    btn.dataset.uid = String(player.uid);
    btn.setAttribute(
      "aria-selected",
      String(previous != null && player.uid === previous),
    );

    const faceWrap = document.createElement("span");
    faceWrap.className = "squad-evo-player-face-wrap has-no-face";
    faceWrap.setAttribute("aria-hidden", "true");
    const face = document.createElement("img");
    face.className = "squad-evo-player-face";
    face.alt = "";
    face.decoding = "async";
    bindPlayerFace(face, player.uid, {
      onReady: () => faceWrap.classList.remove("has-no-face"),
      onMissing: () => faceWrap.classList.add("has-no-face"),
    });
    faceWrap.append(face);

    const name = document.createElement("span");
    name.className = "squad-evo-player-option-name";
    name.textContent = player.name || String(player.uid);

    const n = player.attributeHistory?.length ?? 0;
    btn.append(faceWrap, name);
    if (n > 0) {
      const meta = document.createElement("span");
      meta.className = "squad-evo-player-option-meta";
      meta.textContent = String(n);
      btn.append(meta);
    }

    btn.addEventListener("click", () => {
      selectSquadEvolutionPlayer(player.uid);
      closeSquadEvolutionPlayerList();
      squadEvolutionPlayerTriggerEl.focus();
    });

    li.append(btn);
    squadEvolutionPlayerListEl.append(li);
  }

  if (previous != null && sorted.some((p) => p.uid === previous)) {
    setSquadEvolutionPlayerTrigger(
      sorted.find((p) => p.uid === previous) ?? null,
    );
  } else if (sorted[0]) {
    setSquadEvolutionPlayerTrigger(sorted[0]);
  } else {
    setSquadEvolutionPlayerTrigger(null);
  }
}

function evolutionHistoryFor(player: RosterPlayer) {
  return filterAttributeHistory(player.attributeHistory ?? []);
}

function personalityHistoryFor(player: RosterPlayer) {
  const snaps = getPlayerHaHistory(
    haHistoryStore,
    rosterMeta.clubId ?? null,
    player.uid,
  );
  return haSnapshotsToHistoryPoints(snaps);
}

function historyForAttrId(player: RosterPlayer, id: EvolutionAttrId) {
  return id.startsWith('general.')
    ? personalityHistoryFor(player)
    : evolutionHistoryFor(player);
}

function roleDefaultEvolutionAttrs(player: RosterPlayer): EvolutionAttrId[] {
  const history = evolutionHistoryFor(player);
  const defaults = defaultEvolutionAttrIds(player).filter((id) =>
    history.some((p) => historyPointValue(p, id) != null),
  );
  if (defaults.length > 0) return defaults;
  return defaultEvolutionAttrIds(player).slice(0, 4);
}

function selectableEvolutionIdsWithHistory(
  player: RosterPlayer,
): EvolutionAttrId[] {
  return allSelectableEvolutionIds(player).filter((id) => {
    const history = historyForAttrId(player, id);
    return (
      history.some((p) => historyPointValue(p, id) != null) ||
      liveAttrValue(player, id) != null
    );
  });
}

function effectiveEvolutionAttrs(player: RosterPlayer): EvolutionAttrId[] {
  if (squadEvolutionAttrOverride === 'all') {
    return selectableEvolutionIdsWithHistory(player);
  }
  if (squadEvolutionAttrOverride === 'none') return [];
  return squadEvolutionAttrs;
}

/** Chart uses CA history when any CA attr is selected; otherwise personality HA. */
function chartHistoryAndAttrs(player: RosterPlayer): {
  history: ReturnType<typeof evolutionHistoryFor>;
  attrs: EvolutionAttrId[];
} {
  const selected = effectiveEvolutionAttrs(player);
  const caSelected = selected.filter((id) => !id.startsWith('general.'));
  const persSelected = selected.filter((id) => id.startsWith('general.'));
  if (caSelected.length > 0) {
    return { history: evolutionHistoryFor(player), attrs: caSelected };
  }
  return { history: personalityHistoryFor(player), attrs: persSelected };
}

function selectSquadEvolutionPlayer(uid: number) {
  const player = findRosterPlayer(uid);
  if (!player) return;
  squadEvolutionUid = uid;
  setSquadEvolutionPlayerTrigger(player);
  for (const opt of squadEvolutionPlayerListEl.querySelectorAll<HTMLButtonElement>(
    '.squad-evo-player-option',
  )) {
    opt.setAttribute('aria-selected', String(opt.dataset.uid === String(uid)));
  }
  squadEvolutionAttrOverride = 'default';
  squadEvolutionHover = null;
  squadEvolutionAttrs = roleDefaultEvolutionAttrs(player);
  squadEvolutionTogglesEl.dataset.sig = '';
  renderSquadEvolution();
}

function clearSquadEvolution() {
  squadEvolutionUid = null;
  squadEvolutionAttrs = [];
  squadEvolutionAttrOverride = 'default';
  squadEvolutionHover = null;
  squadEvolutionChartEl.replaceChildren();
  squadEvolutionTogglesEl.replaceChildren();
  squadEvolutionTogglesEl.dataset.sig = '';
  squadEvolutionSubEl.textContent = '';
  squadEvolutionPlayerListEl.replaceChildren();
  setSquadEvolutionPlayerTrigger(null);
  closeSquadEvolutionPlayerList();
  squadEvoShowAllEl.setAttribute('aria-pressed', 'false');
  squadEvoHideAllEl.setAttribute('aria-pressed', 'false');
  squadEvoVisibilityToolsEl.hidden = false;
}

function appendAttrToggle(
  list: HTMLElement,
  player: RosterPlayer,
  id: EvolutionAttrId,
) {
  const history = historyForAttrId(player, id);
  const { value, delta } = attrValueAndDelta(
    history,
    id,
    liveAttrValue(player, id),
  );
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'squad-evo-toggle';
  btn.dataset.attrId = id;
  const swatch = document.createElement('span');
  swatch.className = 'squad-evo-swatch is-muted';
  swatch.setAttribute('aria-hidden', 'true');
  const text = document.createElement('span');
  text.className = 'squad-evo-toggle-label';
  text.textContent = labelForEvolutionAttr(id);
  const meta = document.createElement('span');
  meta.className = 'squad-evo-toggle-meta';
  const valEl = document.createElement('span');
  valEl.className = 'squad-evo-toggle-val';
  valEl.textContent = value != null ? String(value) : '—';
  const deltaEl = document.createElement('span');
  deltaEl.className = 'squad-evo-toggle-delta';
  const deltaText = formatAttrDelta(delta);
  deltaEl.textContent = deltaText;
  if (delta != null && delta > 0) deltaEl.classList.add('is-up');
  if (delta != null && delta < 0) deltaEl.classList.add('is-down');
  meta.append(valEl, deltaEl);
  btn.append(swatch, text, meta);
  btn.addEventListener('click', () => {
    const current = effectiveEvolutionAttrs(player);
    if (squadEvolutionAttrOverride !== 'default') {
      squadEvolutionAttrOverride = 'default';
      if (current.includes(id)) {
        squadEvolutionAttrs = current.filter((x) => x !== id);
      } else {
        squadEvolutionAttrs = [...current, id];
      }
    } else if (squadEvolutionAttrs.includes(id)) {
      if (squadEvolutionAttrs.length <= 1) return;
      squadEvolutionAttrs = squadEvolutionAttrs.filter((x) => x !== id);
    } else {
      squadEvolutionAttrs = [...squadEvolutionAttrs, id];
    }
    squadEvolutionHover = null;
    renderSquadEvolution();
  });
  list.append(btn);
}

function syncAttrToggleAppearance(
  player: RosterPlayer,
  activeAttrs: EvolutionAttrId[],
) {
  for (const btn of squadEvolutionTogglesEl.querySelectorAll<HTMLButtonElement>(
    '.squad-evo-toggle',
  )) {
    const id = btn.dataset.attrId as EvolutionAttrId | undefined;
    if (!id) continue;
    const on = activeAttrs.includes(id);
    btn.classList.toggle('is-on', on);
    const swatch = btn.querySelector<HTMLElement>('.squad-evo-swatch');
    if (swatch) {
      const color = colorForActiveEvolutionAttr(id, activeAttrs);
      if (color) {
        swatch.style.background = color;
        swatch.classList.remove('is-muted', 'is-off');
      } else {
        swatch.style.background = '';
        swatch.classList.add('is-muted');
        swatch.classList.remove('is-off');
      }
    }
    const history = historyForAttrId(player, id);
    const { value, delta } = attrValueAndDelta(
      history,
      id,
      liveAttrValue(player, id),
    );
    const valEl = btn.querySelector<HTMLElement>('.squad-evo-toggle-val');
    const deltaEl = btn.querySelector<HTMLElement>('.squad-evo-toggle-delta');
    if (valEl) valEl.textContent = value != null ? String(value) : '—';
    if (deltaEl) {
      const deltaText = formatAttrDelta(delta);
      deltaEl.textContent = deltaText;
      deltaEl.classList.toggle('is-up', delta != null && delta > 0);
      deltaEl.classList.toggle('is-down', delta != null && delta < 0);
    }
  }
}

function renderSquadEvolution() {
  if (!(isSquadUnitMode(squadViewMode) && squadUnitView === 'attributes')) return;
  if (squadEvolutionUid == null) {
    squadEvolutionSubEl.textContent = '';
    squadEvolutionChartEl.replaceChildren();
    squadEvolutionChartEl.title = 'Select a player';
    return;
  }
  const player = findRosterPlayer(squadEvolutionUid);
  if (!player) {
    clearSquadEvolution();
    return;
  }

  squadEvoVisibilityToolsEl.hidden = false;
  const caHistory = evolutionHistoryFor(player);
  const { history: chartHistory, attrs: chartAttrs } =
    chartHistoryAndAttrs(player);
  const activeAttrs = effectiveEvolutionAttrs(player);

  squadEvolutionSubEl.textContent = '';
  squadEvolutionChartEl.title =
    caHistory.length === 0 && chartAttrs.every((id) => !id.startsWith('general.'))
      ? 'No CA history in this save extract — re-upload the Career Save'
      : '';

  const series = buildEvolutionSeries(chartHistory, chartAttrs);
  const chartH = Math.max(
    120,
    Math.min(200, Math.floor(window.innerHeight * 0.18)),
  );
  squadEvolutionChartEl.replaceChildren(
    renderEvolutionChartSvg(series, {
      height: chartH,
      hover: squadEvolutionHover,
      dates: chartHistory.map((p) => p.date),
    }),
  );

  squadEvoShowAllEl.setAttribute(
    'aria-pressed',
    String(squadEvolutionAttrOverride === 'all'),
  );
  squadEvoHideAllEl.setAttribute(
    'aria-pressed',
    String(squadEvolutionAttrOverride === 'none'),
  );

  const layoutKind =
    player.attributeHistory?.at(-1)?.kind ??
    player._extract?.kind ??
    'outfield';
  const sig = `${player.uid}:${layoutKind}:unified`;
  if (squadEvolutionTogglesEl.dataset.sig !== sig) {
    squadEvolutionTogglesEl.dataset.sig = sig;
    squadEvolutionTogglesEl.replaceChildren();
    for (const category of evolutionCategoriesWithPersonality(player)) {
      const ids = category.ids.filter((id) => {
        const history = historyForAttrId(player, id);
        return (
          history.some((p) => historyPointValue(p, id) != null) ||
          liveAttrValue(player, id) != null
        );
      });
      if (ids.length === 0) continue;
      const col = document.createElement('div');
      col.className = 'squad-evo-cat';
      col.dataset.category = category.id;
      const title = document.createElement('h3');
      title.className = 'squad-evo-cat-title';
      title.textContent = category.label;
      const list = document.createElement('div');
      list.className = 'squad-evo-cat-list';
      for (const id of ids) appendAttrToggle(list, player, id);
      col.append(title, list);
      squadEvolutionTogglesEl.append(col);
    }
  }
  syncAttrToggleAppearance(player, activeAttrs);
}

squadViewFirstTeamEl.addEventListener("click", () => {
  squadUnitView = "personalities";
  setSquadViewMode("firstTeam");
});
squadViewReservesEl.addEventListener("click", () => {
  squadUnitView = "personalities";
  setSquadViewMode("reserves");
});
squadViewUnder19sEl.addEventListener("click", () => {
  squadUnitView = "personalities";
  setSquadViewMode("under19s");
});
squadViewLoansEl.addEventListener("click", () => {
  squadUnitView = "personalities";
  setSquadViewMode("loans");
});
squadViewMentoringEl.addEventListener("click", () =>
  setSquadViewMode("mentoring"),
);

squadEvolutionPlayerTriggerEl.addEventListener("click", () => {
  if (squadEvolutionPlayerListEl.hidden) openSquadEvolutionPlayerList();
  else closeSquadEvolutionPlayerList();
});

document.addEventListener("pointerdown", (event) => {
  if (squadEvolutionPlayerListEl.hidden) return;
  const target = event.target;
  if (!(target instanceof Node)) return;
  if (squadEvolutionPlayerPickerEl.contains(target)) return;
  closeSquadEvolutionPlayerList();
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (squadEvolutionPlayerListEl.hidden) return;
  closeSquadEvolutionPlayerList();
  squadEvolutionPlayerTriggerEl.focus();
});

squadEvoShowAllEl.addEventListener("click", () => {
  if (squadEvolutionUid == null) return;
  const player = findRosterPlayer(squadEvolutionUid);
  if (!player) return;
  if (squadEvolutionAttrOverride === "all") {
    squadEvolutionAttrOverride = "default";
    squadEvolutionAttrs = roleDefaultEvolutionAttrs(player);
  } else {
    squadEvolutionAttrOverride = "all";
  }
  squadEvolutionHover = null;
  renderSquadEvolution();
});

squadEvoHideAllEl.addEventListener("click", () => {
  if (squadEvolutionUid == null) return;
  const player = findRosterPlayer(squadEvolutionUid);
  if (!player) return;
  if (squadEvolutionAttrOverride === "none") {
    squadEvolutionAttrOverride = "default";
    squadEvolutionAttrs = roleDefaultEvolutionAttrs(player);
  } else {
    squadEvolutionAttrOverride = "none";
  }
  squadEvolutionHover = null;
  renderSquadEvolution();
});

squadEvolutionChartEl.addEventListener("mousemove", (event) => {
  if (
    !(isSquadUnitMode(squadViewMode) && squadUnitView === "attributes") ||
    squadEvolutionUid == null
  ) {
    return;
  }
  const player = findRosterPlayer(squadEvolutionUid);
  if (!player) return;
  const { history, attrs } = chartHistoryAndAttrs(player);
  if (history.length === 0) return;
  const svg = squadEvolutionChartEl.querySelector("svg");
  if (!svg) return;
  const series = buildEvolutionSeries(history, attrs);
  const ctm = svg.getScreenCTM();
  if (!ctm) return;
  const local = new DOMPoint(event.clientX, event.clientY).matrixTransform(
    ctm.inverse(),
  );
  const vb = svg.viewBox.baseVal;
  const hit = hitTestEvolutionPoint(series, {
    plotX: local.x,
    plotY: local.y,
    width: vb.width,
    height: vb.height,
    history,
  });
  const same =
    (hit == null && squadEvolutionHover == null) ||
    (hit != null &&
      squadEvolutionHover != null &&
      hit.index === squadEvolutionHover.index &&
      hit.attrId === squadEvolutionHover.attrId);
  if (!same) {
    squadEvolutionHover = hit;
    renderSquadEvolution();
  }
});

squadEvolutionChartEl.addEventListener("mouseleave", () => {
  if (squadEvolutionHover == null) return;
  squadEvolutionHover = null;
  renderSquadEvolution();
});

function applyActiveRosterFromStore(options?: {
  soft?: boolean;
  /** Default true. Persist path sets false so a just-written store is not clobbered. */
  reload?: boolean;
}) {
  // Re-read from localStorage so a failed / HMR mid-init cannot leave an
  // empty in-memory store while Career Saves still exist in the browser.
  if (options?.reload !== false) {
    try {
      rosterStore = loadRosterStore();
      haHistoryStore = backfillHaHistoryFromRosterStore(
        loadHaHistoryStore(),
        rosterStore,
      );
    } catch (err) {
      console.error("Failed to reload Career Saves from localStorage", err);
    }
  }
  const name = rosterStore.activeSaveName;
  const entry = name ? rosterStore.saves[name] : undefined;
  const keepViewMode = squadViewMode;
  const soft = Boolean(options?.soft);
  if (soft) {
    squadEvolutionHover = null;
  } else {
    clearSquadEvolution();
  }
  if (!entry) {
    const names = listRosterSaveNames(rosterStore);
    if (names.length > 0) {
      rosterStore = setActiveRoster(rosterStore, names[0]!);
      applyActiveRosterFromStore(options);
      return;
    }
    firstTeamPlayers = [];
    reservesPlayers = [];
    under19sPlayers = [];
    rosterPlayers = [];
    rosterMeta = { source: "empty" };
    scoutState = { players: [], missing: true };
    invalidateMentoringCache();
    if (keepViewMode !== "firstTeam") setSquadViewMode(keepViewMode);
    return;
  }
  firstTeamPlayers = (entry.players ?? []).map((p) =>
    normalizeRosterPlayer(p as LegacyRosterPlayer),
  );
  reservesPlayers = (entry.reserves?.players ?? []).map((p) =>
    normalizeRosterPlayer(p as LegacyRosterPlayer),
  );
  under19sPlayers = (entry.u19?.players ?? []).map((p) =>
    normalizeRosterPlayer(p as LegacyRosterPlayer),
  );
  syncActiveSquadPlayers();
  const clubId = entry.clubId;
  rosterMeta = {
    source: "save",
    saveName: entry.saveName,
    clubId,
    teamId: entry.teamId,
    clubName: entry.clubName,
    clubNameShort: entry.clubNameShort,
    elapsedMs: entry.elapsedMs,
    extractedAt: entry.extractedAt,
    dateCreated: entry.dateCreated ?? null,
    lastSaved: entry.lastSaved ?? null,
    gameDate: entry.gameDate ?? null,
  };
  const fav = entry.favouredClub;
  if (fav) {
    scoutState = {
      saveName: entry.saveName,
      clubId: fav.clubId ?? entry.clubId,
      clubName: fav.clubName ?? entry.clubName ?? null,
      clubNameShort: fav.clubNameShort ?? entry.clubNameShort ?? null,
      players: (fav.players ?? []).map((p) => ({
        uid: Number(p.uid),
        name: p.name ?? null,
        affinity: Number(p.affinity) || 100,
        ca: p.ca != null ? Number(p.ca) : null,
        pa: p.pa != null ? Number(p.pa) : null,
      })),
      hitCount: fav.hitCount,
      elapsedMs: fav.elapsedMs,
      error: fav.error ?? null,
      missing: false,
    };
  } else {
    scoutState = {
      saveName: entry.saveName,
      clubId: entry.clubId,
      clubName: entry.clubName ?? null,
      clubNameShort: entry.clubNameShort ?? null,
      players: [],
      missing: true,
      error: null,
    };
  }
  // Mentoring groups persist by save name — only soft-reset session when save changes.
  const persistKey = mentoringPersistKey();
  if (mentoringCache.persistKey !== persistKey) {
    mentoringCache.persistKey = "";
    mentoringCache.sessionKey = "";
    mentoringCache.candidates = null;
    mentoringCache.suggestions = [];
    mentoringCache.suggestionsStatus = "idle";
    mentoringRenderFingerprint = "";
  }
  if (pendingSquadUnitView) {
    squadUnitView = pendingSquadUnitView;
    pendingSquadUnitView = null;
  }
  if (keepViewMode !== "firstTeam" || squadUnitView !== "personalities") {
    setSquadViewMode(keepViewMode);
  }
}

// Roster store is applied once at the end of module init (after DOM bindings /
// mentoring helpers are out of TDZ). Calling it here crashed the whole app:
// mentoringPersistKey before initialization.

function isAppTool(value: string | null | undefined): value is AppTool {
  return value === "rank" || value === "roster";
}

/** Former Attributes/Compare pages → open HAS Rank probe modal once. */
let pendingOpenProbe = false;
let pendingOpenProbeMode: ProbeMode = "single";
let probeMode: ProbeMode = "single";
function isProbeMode(value: string | null | undefined): value is ProbeMode {
  return value === "single" || value === "compare";
}

function readHashToolRaw(): string {
  return window.location.hash.replace(/^#/, "");
}

/** Parse `#roster/mentoring` / `#roster/reserves/attributes` into tool + squad tab. */
function readHashRoute(): {
  tool: AppTool | null;
  squadView: SquadViewMode | null;
  unitView: SquadUnitView | null;
} {
  const raw = readHashToolRaw();
  if (!raw) return { tool: null, squadView: null, unitView: null };
  const parts = raw.split("/");
  const head = parts[0];
  const tab = parts[1];
  const detail = parts[2];
  if (head === "roster" || head === "squad") {
    const mapped =
      tab == null || tab === "" || tab === "personalities" || tab === "first-team"
        ? "firstTeam"
        : tab === "u19" || tab === "under-19s" || tab === "under19"
          ? "under19s"
          : tab === "reserve" || tab === "ii"
            ? "reserves"
            : tab === "attributes"
              ? "firstTeam"
              : tab === "penalties" || tab === "scouting" || tab === "scout"
                ? "firstTeam"
                : tab;
    const unitView: SquadUnitView | null =
      detail === "attributes" || tab === "attributes"
        ? "attributes"
        : detail === "personalities" || mapped === "mentoring"
          ? mapped === "mentoring"
            ? null
            : "personalities"
          : null;
    return {
      tool: "roster",
      squadView: isSquadViewMode(mapped) ? mapped : null,
      unitView,
    };
  }
  if (head === "scout" || head === "scouting") {
    return { tool: "roster", squadView: "firstTeam", unitView: null };
  }
  if (head === "checker" || head === "compare" || head === "rank") {
    return { tool: "rank", squadView: null, unitView: null };
  }
  if (isAppTool(head)) return { tool: head, squadView: null, unitView: null };
  return { tool: null, squadView: null, unitView: null };
}

function readStoredTool(): AppTool | null {
  const hashRoute = readHashRoute();
  if (hashRoute.squadView) pendingSquadViewMode = hashRoute.squadView;
  if (hashRoute.unitView) pendingSquadUnitView = hashRoute.unitView;
  const stored = (() => {
    try {
      return window.localStorage.getItem(TOOL_STORAGE_KEY);
    } catch {
      return null;
    }
  })();
  // Former dedicated Mentoring tool → Squad mentoring tab.
  if (readHashToolRaw() === "mentoring") {
    pendingSquadViewMode = "mentoring";
    return "roster";
  }
  // Former top-level Scouting tool → First Team.
  if (hashRoute.tool === "roster" && hashRoute.squadView === "firstTeam") {
    return "roster";
  }
  // Former Attributes page / #checker → HAS Rank + single probe.
  if (readHashToolRaw() === "checker") {
    pendingOpenProbe = true;
    pendingOpenProbeMode = "single";
    return "rank";
  }
  // Former Compare page → HAS Rank + compare probe.
  if (readHashToolRaw() === "compare") {
    pendingOpenProbe = true;
    pendingOpenProbeMode = "compare";
    return "rank";
  }
  if (hashRoute.tool) return hashRoute.tool;
  if (isAppTool(stored)) return stored;
  return null;
}

function persistActiveTool(tool: AppTool) {
  try {
    window.localStorage.setItem(TOOL_STORAGE_KEY, tool);
  } catch {
    // ignore private-mode / quota failures
  }
  const view = pendingSquadViewMode ?? squadViewMode;
  const nextHash =
    tool === "roster" ? rosterHashForView(view) : `#${tool}`;
  if (window.location.hash !== nextHash) {
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${nextHash}`);
  }
}

const CHECKER_DRAFT_KEY = "fmt.checkerDraft";

type CheckerDraft = {
  personality: string;
  mediaHandling: string;
  determination: string;
  leadership: string;
  age: string;
  isRegen: boolean;
};

function readCheckerDraft(): CheckerDraft | null {
  try {
    const raw = window.localStorage.getItem(CHECKER_DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<CheckerDraft>;
    if (!parsed || typeof parsed !== "object") return null;
    return {
      personality: typeof parsed.personality === "string" ? parsed.personality : "",
      mediaHandling:
        typeof parsed.mediaHandling === "string" ? parsed.mediaHandling : "",
      determination:
        typeof parsed.determination === "string" ? parsed.determination : "",
      leadership: typeof parsed.leadership === "string" ? parsed.leadership : "",
      age: typeof parsed.age === "string" ? parsed.age : "",
      isRegen: Boolean(parsed.isRegen),
    };
  } catch {
    return null;
  }
}

function persistCheckerDraft() {
  const draft: CheckerDraft = {
    personality: checkPersonalityEl.value,
    mediaHandling: checkMediaEl.value,
    determination: checkDeterminationEl.value,
    leadership: checkLeadershipEl.value,
    age: checkAgeEl.value,
    isRegen: checkIsRegenEl.checked,
  };
  try {
    window.localStorage.setItem(CHECKER_DRAFT_KEY, JSON.stringify(draft));
  } catch {
    // ignore private-mode / quota failures
  }
}

function restoreCheckerDraft() {
  const draft = readCheckerDraft();
  if (!draft) return;
  checkPersonalityEl.value = draft.personality;
  checkMediaEl.value = draft.mediaHandling;
  checkDeterminationEl.value = draft.determination;
  checkLeadershipEl.value = draft.leadership;
  checkAgeEl.value = draft.age;
  checkIsRegenEl.checked = draft.isRegen;
  syncRegenChip(checkIsRegenEl);
  // Preserve restored Det/Lea until personality/media/regen actually change.
  const person = findPersonality(catalog, draft.personality.trim());
  if (person && draft.mediaHandling.trim()) {
    try {
      const media = findMediaHandling(
        catalog,
        parseMediaHandlingInput(draft.mediaHandling),
      );
      if (media) {
        lastCheckerSyncedComboKey = checkerComboKey(
          person.id,
          formatMediaHandlingLabel(media.styles),
          draft.isRegen,
        );
      }
    } catch {
      // leave key empty — next commit may resync
    }
  }
  syncQuickPicks();
}

/** Active tool pane — independent of drawer saves/players panel. */
let activeTool: AppTool = (() => {
  return readStoredTool() ?? "rank";
})();

/** Default: mixed REAL+NEWGEN list with labels where HA differs. */
let rankerPopulation: RankPopulationMode = "mixed";
/** Midpoints vs min–max bands in attribute columns. */
let rankerValueMode: "mid" | "band" = "mid";
/** Cached HA ranking — list may re-order by column sort without re-ranking. */
let lastRankerEntries: ComboRankEntry[] = [];
/** Catalog-relative elite HAS floor (top 25% unique) from last ranker build. */
let catalogEliteHasFloor = HIDDEN_QUALITY_GOOD_FLOOR;
/** Catalog-relative poor HAS ceiling (bottom 25% unique) from last ranker build. */
let catalogPoorHasCeiling = HIDDEN_QUALITY_BAD_CEILING;
type RankerSortKey = "has" | keyof ComboRankEntry["mids"];
let rankerSortKey: RankerSortKey = "has";
/** false = high→low (default for HAS and attrs). */
let rankerSortAsc = false;

type RankerNumericFilterKey = RankerSortKey;
type RankerTextFilterKey = "personality" | "mediaHandling" | "player";
type RankerFilterKey = RankerNumericFilterKey | RankerTextFilterKey;
type RankerFilterOp = "gte" | "lte" | "eq" | "neq";
type RankerFilterJoin = "and" | "or";
type RankerFilter = {
  id: string;
  key: RankerFilterKey;
  op: RankerFilterOp;
  /** Attr/HAS: 1–20 (or score). Text filters: personality / media / REAL|NEWGEN. */
  value: number | string;
};
let rankerFilters: RankerFilter[] = [];
/** Join between filters[i] and filters[i + 1] — length filters.length - 1. */
let rankerFilterJoins: RankerFilterJoin[] = [];
let rankerFilterSeq = 0;

const rankerFilterRowsEl = document.querySelector<HTMLElement>("#ranker-filter-rows")!;
const rankerFilterAddEl = document.querySelector<HTMLButtonElement>("#ranker-filter-add")!;
const rankerFilterToggleEl = document.querySelector<HTMLButtonElement>("#ranker-filter-toggle")!;
const rankerFilterPopoverEl = document.querySelector<HTMLElement>("#ranker-filter-popover")!;
const rankerFilterCountEl = document.querySelector<HTMLElement>("#ranker-filter-count")!;

let rankerMatches: HTMLTableRowElement[] = [];
let rankerMatchIndex = 0;

const personalityEl = document.querySelector<HTMLInputElement>("#personality")!;
const mediaEl = document.querySelector<HTMLInputElement>("#mediaHandling")!;
const personalityListEl = document.querySelector<HTMLUListElement>("#personality-list")!;
const mediaListEl = document.querySelector<HTMLUListElement>("#media-list")!;
const determinationEl = document.querySelector<HTMLInputElement>("#determination")!;
const leadershipEl = document.querySelector<HTMLInputElement>("#leadership")!;
const isRegenEl = document.querySelector<HTMLInputElement>("#isRegen")!;
const isRegenChipEl = document.querySelector<HTMLButtonElement>("#isRegen-chip")!;
const ageEl = document.querySelector<HTMLInputElement>("#age")!;
const statusEl = document.querySelector<HTMLElement>("#status")!;
const attrBodyEl = document.querySelector<HTMLTableSectionElement>("#attr-body")!;
const haScoreEl = document.querySelector<HTMLElement>("#ha-score")!;
const haRankEl = document.querySelector<HTMLElement>("#ha-rank")!;
const haScoreValueEl = document.querySelector<HTMLElement>("#ha-score-value")!;
const mentoringStatusEl = document.querySelector<HTMLElement>("#mentoring-status")!;
const mentoringEmptyEl = document.querySelector<HTMLElement>("#mentoring-empty")!;
const mentoringCardsEl = document.querySelector<HTMLElement>("#mentoring-cards")!;
const mentoringAddBtn = document.querySelector<HTMLButtonElement>("#mentoring-add-btn")!;
const mentoringPickerDialogEl = document.querySelector<HTMLDialogElement>(
  "#mentoring-picker-dialog",
)!;
const mentoringPickerCountEl = document.querySelector<HTMLElement>("#mentoring-picker-count")!;
const mentoringPickerCloseBtn = document.querySelector<HTMLButtonElement>(
  "#mentoring-picker-close",
)!;
const mentoringPickerBodyEl = document.querySelector<HTMLTableSectionElement>(
  "#mentoring-picker-body",
)!;
const mentoringPickerSuggestBtn = document.querySelector<HTMLButtonElement>(
  "#mentoring-picker-suggest",
)!;
const mentoringPickerClearBtn = document.querySelector<HTMLButtonElement>(
  "#mentoring-picker-clear",
)!;
const mentoringDetailDialogEl = document.querySelector<HTMLDialogElement>(
  "#mentoring-detail-dialog",
)!;
const mentoringDetailTitleEl = document.querySelector<HTMLElement>("#mentoring-detail-title")!;
const mentoringDetailVerdictEl = document.querySelector<HTMLElement>("#mentoring-detail-verdict")!;
const mentoringDetailSeatsEl = document.querySelector<HTMLElement>("#mentoring-detail-seats")!;
const mentoringDetailAttrsEl = document.querySelector<HTMLElement>("#mentoring-detail-attrs")!;
const mentoringDetailCloseBtn = document.querySelector<HTMLButtonElement>(
  "#mentoring-detail-close",
)!;
const mentoringDynamicsDialogEl = document.querySelector<HTMLDialogElement>(
  "#mentoring-dynamics-dialog",
)!;
const mentoringDynamicsTitleEl = document.querySelector<HTMLElement>(
  "#mentoring-dynamics-title",
)!;
const mentoringDynamicsSubtitleEl = document.querySelector<HTMLElement>(
  "#mentoring-dynamics-subtitle",
)!;
const mentoringDynamicsStatusEl = document.querySelector<HTMLElement>(
  "#mentoring-dynamics-status",
)!;
const mentoringDynamicsCloseBtn = document.querySelector<HTMLButtonElement>(
  "#mentoring-dynamics-close",
)!;
const mentoringDynamicsClearBtn = document.querySelector<HTMLButtonElement>(
  "#mentoring-dynamics-clear",
)!;
const mentoringDynamicsSaveBtn = document.querySelector<HTMLButtonElement>(
  "#mentoring-dynamics-save",
)!;
const mentoringDynamicsInfluenceEl = document.querySelector<HTMLElement>(
  "#mentoring-dynamics-influence",
)!;
const attrTableEl = document.querySelector<HTMLTableElement>("#attr-table")!;

const checkPersonalityEl = document.querySelector<HTMLInputElement>("#check-personality")!;
const checkMediaEl = document.querySelector<HTMLInputElement>("#check-mediaHandling")!;
const checkPersonalityListEl = document.querySelector<HTMLUListElement>(
  "#check-personality-list",
)!;
const checkMediaListEl = document.querySelector<HTMLUListElement>("#check-media-list")!;
const checkDeterminationEl = document.querySelector<HTMLInputElement>(
  "#check-determination",
)!;
const checkLeadershipEl = document.querySelector<HTMLInputElement>("#check-leadership")!;
const checkDetAttrEl = document.querySelector<HTMLElement>(
  ".check-toolbar-known[data-attribute='determination']",
)!;
const checkLeaAttrEl = document.querySelector<HTMLElement>(
  ".check-toolbar-known[data-attribute='leadership']",
)!;
const checkIsRegenEl = document.querySelector<HTMLInputElement>("#check-isRegen")!;
const checkIsRegenChipEl = document.querySelector<HTMLButtonElement>(
  "#check-isRegen-chip",
)!;
const checkAgeEl = document.querySelector<HTMLInputElement>("#check-age")!;
const checkStatusEl = document.querySelector<HTMLElement>("#check-status")!;
const checkAttrBodyEl = document.querySelector<HTMLTableSectionElement>(
  "#check-attr-body",
)!;
const checkTableWrapEl = document.querySelector<HTMLElement>("#check-table-wrap")!;
const checkRadarWrapEl = document.querySelector<HTMLElement>("#check-radar-wrap")!;
const checkRadarEl = document.querySelector<SVGSVGElement>("#check-radar")!;
const checkViewModeEl = document.querySelector<HTMLElement>(".check-view-mode")!;
const checkComboCardEl = document.querySelector<HTMLElement>("#check-combo-card")!;
const checkComboRankEl = document.querySelector<HTMLElement>("#check-combo-rank")!;
const checkComboPersonalityEl = document.querySelector<HTMLElement>(
  "#check-combo-personality",
)!;
const checkComboMediaEl = document.querySelector<HTMLElement>("#check-combo-media")!;
const checkComboMetaEl = document.querySelector<HTMLElement>("#check-combo-meta")!;
const checkComboWorseEl = document.querySelector<HTMLButtonElement>(
  "#check-combo-worse",
)!;
const checkComboBetterEl = document.querySelector<HTMLButtonElement>(
  "#check-combo-better",
)!;
const checkCarouselArrowWorseEl = document.querySelector<HTMLButtonElement>(
  "#check-carousel-arrow-worse",
)!;
const checkCarouselArrowBetterEl = document.querySelector<HTMLButtonElement>(
  "#check-carousel-arrow-better",
)!;
const compareSlotsEl = document.querySelector<HTMLElement>("#compare-slots")!;
const compareAddSlotEl = document.querySelector<HTMLButtonElement>("#compare-add-slot")!;
const compareMatrixScrollEl = document.querySelector<HTMLElement>(
  "#compare-matrix-scroll",
)!;
const compareMatrixHeadEl = document.querySelector<HTMLTableSectionElement>(
  "#compare-matrix-head",
)!;
const compareMatrixBodyEl = document.querySelector<HTMLTableSectionElement>(
  "#compare-matrix-body",
)!;
const compareStatusEl = document.querySelector<HTMLElement>("#compare-status")!;
const compareRadarWrapEl = document.querySelector<HTMLElement>("#compare-radar-wrap")!;
const compareRadarEl = document.querySelector<SVGSVGElement>("#compare-radar")!;
const compareRadarLegendEl = document.querySelector<HTMLUListElement>(
  "#compare-radar-legend",
)!;
const compareViewModeEl = document.querySelector<HTMLElement>(".compare-view-mode")!;
const comparePlotModeEl = document.querySelector<HTMLSelectElement>(
  "#compare-plot-mode",
)!;

const CASE_MODE: CaseMode = "union_feasible";

type ImpliedVisible = EstimateResult["impliedVisible"];
type ComboOption = {
  value: string;
  disabled?: boolean;
  violation?: FieldViolation;
  /** Short inline reason shown beside a clicked greyed-out option. */
  hint?: string;
};

let lastImpliedVisible: ImpliedVisible = {};
let lastCheckImpliedVisible: ImpliedVisible = {};
let lastCheckEstimateResult: EstimateResult | null = null;
type CheckViewMode = "table" | "plot";
let checkViewMode: CheckViewMode = "table";
let enforcePass = false;

const saveFormEl = document.querySelector<HTMLFormElement>("#save-form")!;
const playerLabelFormEl = document.querySelector<HTMLFormElement>("#player-label-form")!;
const labelHeadingEl = document.querySelector<HTMLElement>("#label-heading")!;
const labelGameVersionEl = document.querySelector<HTMLSelectElement>("#label-game-version")!;
const labelDatabaseEl = document.querySelector<HTMLSelectElement>("#label-database")!;
const labelDatabaseCustomWrapEl = document.querySelector<HTMLElement>("#label-database-custom-wrap")!;
const labelDatabaseCustomEl = document.querySelector<HTMLInputElement>("#label-database-custom")!;
const labelBrowseDatabaseEl = document.querySelector<HTMLButtonElement>("#label-browse-database")!;
const labelDatabaseClearEl = document.querySelector<HTMLButtonElement>("#label-database-clear")!;
const labelDatabaseFileEl = document.querySelector<HTMLInputElement>("#label-database-file")!;
const labelGameSaveEl = document.querySelector<HTMLInputElement>("#label-game-save")!;
const labelBrowseSaveEl = document.querySelector<HTMLButtonElement>("#label-browse-save")!;
const labelSaveFileEl = document.querySelector<HTMLInputElement>("#label-save-file")!;
const labelPlayerIdEl = document.querySelector<HTMLInputElement>("#label-player-id")!;
const labelPlayerNameEl = document.querySelector<HTMLInputElement>("#label-player-name")!;
const labelPlayerPositionEl = document.querySelector<HTMLInputElement>(
  "#label-player-position",
)!;

let history: HistoryStore = emptyHistoryStore();
let suppressHistory = false;
let suppressLabelSync = false;
let forceCreateNext = false;
let saveTimer: number | undefined;
let historyTimer: number | undefined;
let labelSaveTimer: number | undefined;
let pendingHistory:
  | {
      signals: HistorySignals;
      caseMode: CaseMode;
      result: EstimateResult | null;
      error?: string;
    }
  | undefined;

function newId(): string {
  return crypto.randomUUID();
}

function formatNum(value: number | undefined): string {
  return value !== undefined ? String(value) : "—";
}

function formatStamp(iso: string): string {
  const date = new Date(iso);
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  let hours = date.getHours();
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const period = hours >= 12 ? "PM" : "AM";
  hours = hours % 12;
  if (hours === 0) hours = 12;
  const hourText = String(hours).padStart(2, "0");
  return `${day}/${month}/${year}, ${hourText}:${minutes} ${period}`;
}

function wasEdited(entry: { editedAt?: string; createdAt: string }): boolean {
  return Boolean(entry.editedAt);
}

function sortKey(entry: { editedAt?: string; createdAt: string }): string {
  return entry.editedAt ?? entry.createdAt;
}

function mentalTone(value: number | undefined): "good" | "bad" | "neutral" {
  if (value === undefined) return "neutral";
  if (value > 14) return "good";
  if (value < 11) return "bad";
  return "neutral";
}

let metricTipEl: HTMLElement | undefined;

function ensureMetricTip(): HTMLElement {
  if (metricTipEl?.isConnected) return metricTipEl;
  metricTipEl = document.createElement("div");
  metricTipEl.className = "metric-tip";
  metricTipEl.hidden = true;
  document.body.append(metricTipEl);
  return metricTipEl;
}

function positionMetricTip(host: HTMLElement, tip: HTMLElement) {
  tip.style.transform = "none";
  tip.style.left = "0px";
  tip.style.top = "0px";

  const hostRect = host.getBoundingClientRect();
  const measured = tip.getBoundingClientRect();
  // First paint after unhide can report 0×0 — use CSS max-width fallback so we
  // don't park a wide mentoring matrix off the right edge of the viewport.
  const fallbackW = Math.min(28 * 16, window.innerWidth - 24);
  const fallbackH = Math.min(0.48 * window.innerHeight, 22 * 16);
  const tipW = measured.width >= 8 ? measured.width : fallbackW;
  const tipH = measured.height >= 8 ? measured.height : fallbackH;
  const margin = 8;
  const gap = tip.classList.contains("is-mentoring-matrix") ? 4 : 8;
  const viewW = window.innerWidth;
  const viewH = window.innerHeight;

  // Mentoring attr matrix: park beside the seat so the board stays scannable.
  if (tip.classList.contains("is-mentoring-matrix")) {
    const spaceRight = viewW - hostRect.right - margin;
    const spaceLeft = hostRect.left - margin;
    let left: number;
    const fitsRight = spaceRight >= tipW + gap;
    const fitsLeft = spaceLeft >= tipW + gap;
    if (fitsRight || (!fitsLeft && spaceRight >= spaceLeft)) {
      left = hostRect.right + gap;
      if (left + tipW > viewW - margin) {
        left = Math.max(margin, viewW - tipW - margin);
      }
    } else {
      left = hostRect.left - tipW - gap;
      if (left < margin) left = margin;
    }

    let top = hostRect.top;
    if (top + tipH > viewH - margin) {
      top = Math.max(margin, viewH - tipH - margin);
    }
    if (top < margin) top = margin;

    tip.style.left = `${Math.round(left)}px`;
    tip.style.top = `${Math.round(top)}px`;
    return;
  }

  let left = hostRect.left + hostRect.width / 2 - tipW / 2;
  if (left + tipW > viewW - margin) {
    left = hostRect.right - tipW;
  }
  if (left < margin) left = margin;
  if (left + tipW > viewW - margin) {
    left = Math.max(margin, viewW - tipW - margin);
  }

  let top = hostRect.bottom + 6;
  if (top + tipH > viewH - margin) {
    top = hostRect.top - tipH - 6;
  }
  if (top < margin) top = margin;

  tip.style.left = `${Math.round(left)}px`;
  tip.style.top = `${Math.round(top)}px`;
}

function showMetricTip(host: HTMLElement, text: string) {
  const tip = ensureMetricTip();
  tip.classList.remove("is-roster-attrs");
  tip.replaceChildren();
  tip.textContent = text;
  tip.classList.toggle("is-multiline", text.includes("\n"));
  tip.hidden = false;
  positionMetricTip(host, tip);
}

function showMetricTipNode(host: HTMLElement, content: HTMLElement) {
  const tip = ensureMetricTip();
  tip.classList.remove("is-multiline");
  tip.classList.add("is-roster-attrs");
  tip.replaceChildren(content);
  tip.hidden = false;
  positionMetricTip(host, tip);
}

function hideMetricTip() {
  clearMentoringMatrixTipHide();
  if (!metricTipEl) return;
  metricTipEl.hidden = true;
  metricTipEl.classList.remove("is-multiline", "is-roster-attrs", "is-mentoring-matrix");
  metricTipEl.replaceChildren();
  delete metricTipEl.dataset.pinned;
}

/** Shared hide timer so seat leave → tip enter does not flash-dismiss (T022). */
let mentoringMatrixTipHideTimer = 0;
let mentoringMatrixTipBridgeWired = false;

function clearMentoringMatrixTipHide() {
  if (!mentoringMatrixTipHideTimer) return;
  window.clearTimeout(mentoringMatrixTipHideTimer);
  mentoringMatrixTipHideTimer = 0;
}

function scheduleMentoringMatrixTipHide() {
  if (metricTipEl?.dataset.pinned === "1") return;
  clearMentoringMatrixTipHide();
  mentoringMatrixTipHideTimer = window.setTimeout(() => {
    mentoringMatrixTipHideTimer = 0;
    if (metricTipEl?.dataset.pinned === "1") return;
    if (
      metricTipEl &&
      !metricTipEl.hidden &&
      metricTipEl.classList.contains("is-mentoring-matrix") &&
      metricTipEl.matches(":hover")
    ) {
      return;
    }
    hideMetricTip();
  }, 200);
}

function ensureMentoringMatrixTipHoverBridge() {
  if (mentoringMatrixTipBridgeWired) return;
  mentoringMatrixTipBridgeWired = true;
  const tip = ensureMetricTip();
  tip.addEventListener("mouseenter", () => {
    if (!tip.classList.contains("is-mentoring-matrix")) return;
    clearMentoringMatrixTipHide();
  });
  tip.addEventListener("mouseleave", () => {
    if (!tip.classList.contains("is-mentoring-matrix")) return;
    scheduleMentoringMatrixTipHide();
  });
}

document.addEventListener(
  "click",
  (event) => {
    if (!metricTipEl || metricTipEl.hidden || metricTipEl.dataset.pinned !== "1") {
      return;
    }
    const target = event.target;
    if (!(target instanceof Node)) return;
    if (
      target instanceof Element &&
      (target.closest(".ranker-ha-tip") ||
        target.closest(".mentoring-seat-card.has-attrs-tip") ||
        target.closest(".metric-tip.is-mentoring-matrix"))
    ) {
      return;
    }
    hideMetricTip();
  },
  true,
);

function mentalMetric(
  kind: "determination" | "leadership" | "ha-index",
  label: string,
  value: number | undefined,
): HTMLElement {
  const tone =
    kind === "ha-index"
      ? value === undefined
        ? "neutral"
        : hiddenQualityTone(value, catalogEliteHasFloor, catalogPoorHasCeiling)
      : mentalTone(value);
  const wrap = document.createElement("span");
  wrap.className = `mental-metric ${tone}`;
  wrap.dataset.tip = label;
  wrap.setAttribute("aria-label", label);
  wrap.tabIndex = 0;

  const icon = document.createElement("span");
  icon.className = `mental-icon mental-icon-${kind} ${tone}`;
  icon.setAttribute("aria-hidden", "true");

  const num = document.createElement("span");
  num.className = `num ${value === undefined ? "is-empty" : ""}`;
  num.textContent =
    value === undefined
      ? "—"
      : kind === "ha-index"
        ? formatHaScore(value)
        : formatNum(value);

  wrap.append(icon, num);
  wrap.addEventListener("mouseenter", () => showMetricTip(wrap, label));
  wrap.addEventListener("mouseleave", hideMetricTip);
  wrap.addEventListener("focus", () => showMetricTip(wrap, label));
  wrap.addEventListener("blur", hideMetricTip);
  return wrap;
}

function haScoreFromSnapshot(
  snapshot: PlayerEntry["snapshot"],
): number | undefined {
  const keys = [
    "professionalism",
    "ambition",
    "pressure",
    "temperament",
    "loyalty",
    "sportsmanship",
    "controversy",
  ] as const;
  for (const key of keys) {
    if (!snapshot[key]) return undefined;
  }
  return (
    (snapshot.professionalism!.midpoint +
      snapshot.ambition!.midpoint +
      snapshot.pressure!.midpoint +
      snapshot.temperament!.midpoint +
      snapshot.loyalty!.midpoint +
      snapshot.sportsmanship!.midpoint -
      snapshot.controversy!.midpoint) /
    6
  );
}

function signalsEqual(a: HistorySignals, b: HistorySignals): boolean {
  return (
    a.personality === b.personality &&
    a.mediaHandling === b.mediaHandling &&
    a.determination === b.determination &&
    a.leadership === b.leadership &&
    a.age === b.age &&
    a.isRegen === b.isRegen
  );
}

function parseOptionalInt(raw: string): number | undefined {
  const text = raw.trim();
  if (!text) return undefined;
  const value = Number(text);
  if (!Number.isInteger(value)) {
    throw new Error(`Expected an integer, got "${raw}"`);
  }
  return value;
}

function assertAttrInScale(label: string, value: number | undefined) {
  if (value !== undefined && (value < 1 || value > 20)) {
    throw new Error(`${label} must be between 1 and 20`);
  }
}

function normalizeKey(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[_/]+/g, " ")
    .replace(/-/g, " ")
    .replace(/\s+/g, " ");
}

/** Same tokenization as HAS rank search — multi-word fuzzy includes. */
function rankerSearchTokens(query: string): string[] {
  return normalizeKey(query)
    .replace(/,/g, " ")
    .split(/\s+/)
    .filter(Boolean);
}

function normalizeMatch(query: string, options: string[]): string | undefined {
  const key = query.trim().toLowerCase();
  if (!key) return undefined;
  const exact = options.find((option) => option.toLowerCase() === key);
  if (exact) return exact;

  const tokens = rankerSearchTokens(query);
  if (tokens.length > 0) {
    const tokenHits = options.filter((option) => {
      const haystack = normalizeKey(option).replace(/,/g, " ");
      return tokens.every((token) => haystack.includes(token));
    });
    if (tokenHits.length === 1) return tokenHits[0];
    if (tokenHits.length > 1) {
      const started = tokenHits.find((option) =>
        normalizeKey(option).startsWith(tokens[0]!),
      );
      return started ?? tokenHits[0];
    }
  }

  return (
    options.find((option) => option.toLowerCase().startsWith(key)) ??
    options.find((option) => option.toLowerCase().includes(key))
  );
}

function filterOptions(query: string, options: ComboOption[]): ComboOption[] {
  const tokens = rankerSearchTokens(query);
  if (tokens.length === 0) return options;
  return options.filter((option) => {
    const haystackParts = [option.value];
    const personality = findPersonality(catalog, option.value);
    if (personality) {
      haystackParts.push(personality.id, ...personality.aliases);
    }
    const haystack = normalizeKey(haystackParts.join(" ")).replace(/,/g, " ");
    return tokens.every((token) => haystack.includes(token));
  });
}

const openComboLists = new Set<HTMLUListElement>();

const COMBO_VIEWPORT_GAP = 12;
const COMBO_OVERLAP_PX = 2;

function clearComboListAnchor(listEl: HTMLUListElement) {
  openComboLists.delete(listEl);
  listEl.classList.remove("is-flip-up", "is-anchored");
  for (const prop of [
    "position",
    "top",
    "bottom",
    "left",
    "right",
    "width",
    "max-height",
  ] as const) {
    listEl.style.removeProperty(prop);
  }
}

function scrollComboOptionIntoList(
  listEl: HTMLUListElement,
  target: HTMLElement | null,
) {
  if (!target || !listEl.contains(target)) return;
  const listRect = listEl.getBoundingClientRect();
  const targetRect = target.getBoundingClientRect();
  if (targetRect.bottom > listRect.bottom) {
    listEl.scrollTop += targetRect.bottom - listRect.bottom;
  } else if (targetRect.top < listRect.top) {
    listEl.scrollTop -= listRect.top - targetRect.top;
  }
}

/** Pin open combo lists with position:fixed so they never grow a scrollport. */
function fitComboListToViewport(listEl: HTMLUListElement) {
  if (listEl.hidden) {
    clearComboListAnchor(listEl);
    return;
  }

  const field = listEl.closest(".combo-field");
  const input =
    field?.querySelector<HTMLInputElement>("input:not([type='hidden'])") ??
    document.querySelector<HTMLInputElement>(
      `input[aria-controls="${listEl.id}"]`,
    );
  if (!input) {
    clearComboListAnchor(listEl);
    return;
  }

  const gap = COMBO_VIEWPORT_GAP;
  const rect = input.getBoundingClientRect();
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const spaceBelow = Math.max(0, vh - rect.bottom - gap);
  const spaceAbove = Math.max(0, rect.top - gap);
  const rem = Number.parseFloat(
    getComputedStyle(document.documentElement).fontSize || "16",
  );
  const maxCap = 14 * rem;
  const minComfort = 5.5 * rem;
  const openUp = spaceBelow < minComfort && spaceAbove > spaceBelow;
  const available = openUp ? spaceAbove : spaceBelow;
  const maxHeight = Math.max(3.5 * rem, Math.min(maxCap, available));

  const width = Math.min(rect.width, Math.max(0, vw - gap * 2));
  let left = rect.left;
  if (left + width > vw - gap) left = vw - gap - width;
  if (left < gap) left = gap;

  listEl.classList.add("is-anchored");
  listEl.classList.toggle("is-flip-up", openUp);
  listEl.style.position = "fixed";
  listEl.style.left = `${Math.round(left)}px`;
  listEl.style.width = `${Math.round(width)}px`;
  listEl.style.right = "auto";
  listEl.style.maxHeight = `${Math.floor(maxHeight)}px`;

  if (openUp) {
    listEl.style.top = "auto";
    listEl.style.bottom = `${Math.round(vh - rect.top - COMBO_OVERLAP_PX)}px`;
  } else {
    listEl.style.bottom = "auto";
    listEl.style.top = `${Math.round(rect.bottom - COMBO_OVERLAP_PX)}px`;
  }

  openComboLists.add(listEl);
}

function refitOpenComboLists() {
  for (const listEl of [...openComboLists]) {
    if (listEl.hidden || !listEl.isConnected) {
      clearComboListAnchor(listEl);
      continue;
    }
    fitComboListToViewport(listEl);
  }
}

window.addEventListener("resize", refitOpenComboLists);
window.addEventListener(
  "scroll",
  (event) => {
    // Ignore scrolling inside an open list; only follow page/dock scroll.
    const target = event.target;
    if (
      target instanceof Element &&
      [...openComboLists].some((list) => list === target || list.contains(target))
    ) {
      return;
    }
    refitOpenComboLists();
  },
  true,
);

function renderComboList(
  listEl: HTMLUListElement,
  options: ComboOption[],
  activeIndex: number,
  onPick: (option: ComboOption) => void,
  flash?: { value: string; hint: string } | null,
) {
  listEl.replaceChildren();
  if (options.length === 0) {
    listEl.hidden = true;
    clearComboListAnchor(listEl);
    return;
  }

  options.forEach((option, index) => {
    const item = document.createElement("li");
    item.setAttribute("role", "option");
    item.id = `${listEl.id}-opt-${index}`;
    if (option.disabled) item.dataset.disabled = "true";
    const button = document.createElement("button");
    button.type = "button";
    const label = document.createElement("span");
    label.className = "combo-option-label";
    label.textContent = option.value;
    button.append(label);
    // Keep clickable so an attempt can surface temporary constraint feedback.
    if (option.disabled) {
      button.setAttribute("aria-disabled", "true");
      if (option.violation) {
        button.title = option.violation.message;
        button.setAttribute(
          "aria-label",
          `${option.value}: ${option.violation.message}`,
        );
      }
      if (flash && flash.value === option.value && flash.hint) {
        item.dataset.constraintFlash = "true";
        const hint = document.createElement("span");
        hint.className = "combo-option-hint";
        hint.setAttribute("role", "status");
        hint.textContent = flash.hint;
        button.append(hint);
      }
    }
    if (index === activeIndex) {
      button.setAttribute("aria-selected", "true");
      item.dataset.active = "true";
    }
    button.addEventListener("mousedown", (event) => {
      event.preventDefault();
      onPick(option);
    });
    item.append(button);
    listEl.append(item);
  });
  listEl.hidden = false;
  fitComboListToViewport(listEl);

  const flashed = listEl.querySelector<HTMLElement>('[data-constraint-flash="true"]');
  const active = listEl.querySelector<HTMLElement>('[data-active="true"]');
  // Scroll only inside the list — never ancestors (that paginated the checker dock).
  scrollComboOptionIntoList(listEl, flashed ?? active);
}

const comboFlashTimers = new WeakMap<HTMLElement, number>();

/**
 * Form-state violations after a personality is already chosen
 * (e.g. user turns Regen off again).
 */
function personalityBlockReason(
  personality: PersonalityDefinition,
  isRegen: boolean,
  age: number | undefined,
): FieldViolation | null {
  for (const rule of personality.conditionals) {
    if (rule.kind === "regen_only" && !isRegen) {
      return {
        field: "isRegen",
        message: `${personality.id} is marked regen-only — enable Regen / newgen to use this personality`,
      };
    }
    if (rule.kind === "min_age" && age !== undefined && age <= rule.age) {
      return {
        field: "age",
        message: `${personality.id} requires age over ${rule.age} (currently ${age})`,
      };
    }
  }
  return null;
}

function knownAttrOutOfBand(
  personality: PersonalityDefinition,
  attribute: "determination" | "leadership",
  value: number | undefined,
): { violation: FieldViolation; hint: string } | null {
  if (value === undefined) return null;
  const band = personality.bands[attribute];
  if (!band) return null;
  if (value >= band.min && value <= band.max) return null;
  const label = attribute === "determination" ? "Determination" : "Leadership";
  const short = attribute === "determination" ? "Det" : "Lea";
  return {
    violation: {
      field: attribute,
      message: `${personality.id} requires ${label} ${band.min}–${band.max} (currently ${value})`,
    },
    hint: `Requires ${short} ${band.min}–${band.max}`,
  };
}

type ListConstraint = {
  violation: FieldViolation;
  hint: string;
};

/**
 * Greys out a personality only when already-set inputs conflict.
 * Unset age / Regen / Det / Lead / media do not block — those get auto-filled on pick.
 */
function personalityListViolation(
  personality: PersonalityDefinition,
  age: number | undefined,
  media: MediaHandlingDefinition | undefined,
  determination: number | undefined,
  leadership: number | undefined,
): ListConstraint | null {
  for (const rule of personality.conditionals) {
    if (rule.kind === "min_age" && age !== undefined && age <= rule.age) {
      return {
        violation: {
          field: "age",
          message: `${personality.id} requires age over ${rule.age} (currently ${age})`,
        },
        hint: `Requires age over ${rule.age}`,
      };
    }
  }
  const detConflict = knownAttrOutOfBand(
    personality,
    "determination",
    determination,
  );
  if (detConflict) return detConflict;
  const leadConflict = knownAttrOutOfBand(
    personality,
    "leadership",
    leadership,
  );
  if (leadConflict) return leadConflict;
  if (media && !isPersonalityMediaCompatible(personality, media)) {
    return {
      violation: comboConflictViolation(personality, media, "mediaHandling"),
      hint: "Conflicts with media",
    };
  }
  return null;
}

type PersonalityFieldSet = {
  ageEl: HTMLInputElement;
  isRegenEl: HTMLInputElement;
  determinationEl: HTMLInputElement;
  leadershipEl: HTMLInputElement;
};

/**
 * When the form is blank (or violates soft prerequisites), fill / nudge what
 * the personality requires so the pick can succeed without greying everything out.
 */
function applyPersonalityPrerequisites(
  personality: PersonalityDefinition,
  fields: PersonalityFieldSet,
) {
  for (const rule of personality.conditionals) {
    if (rule.kind === "regen_only" && !fields.isRegenEl.checked) {
      setIsRegen(fields.isRegenEl, true);
    }
    if (rule.kind === "min_age") {
      const age = safeOptionalInt(fields.ageEl.value);
      // Catalog rule is strict “over N” (age > N), so land on N + 1.
      if (age === undefined || age <= rule.age) {
        fields.ageEl.value = String(rule.age + 1);
      }
    }
  }

  for (const attribute of ["determination", "leadership"] as const) {
    const input =
      attribute === "determination"
        ? fields.determinationEl
        : fields.leadershipEl;
    const band = personality.bands[attribute];
    if (!band) continue;
    const current = safeOptionalInt(input.value);
    if (current === undefined) {
      // Only auto-fill blanks when the personality actually constrains the floor / pin.
      if (band.min === band.max || band.min > 1) {
        input.value = String(band.min);
      }
      continue;
    }
    // Clamp known attrs that fall outside this personality’s band (e.g. carousel).
    if (current < band.min || current > band.max) {
      input.value = String(bandMidpoint(band));
    }
  }
}

function selectedPersonality(): PersonalityDefinition | undefined {
  const raw = personalityEl.value.trim();
  if (!raw) return undefined;
  return findPersonality(catalog, raw);
}

function selectedMedia(): MediaHandlingDefinition | undefined {
  const raw = mediaEl.value.trim();
  if (!raw) return undefined;
  try {
    const styles = parseMediaHandlingInput(raw);
    return findMediaHandling(catalog, styles);
  } catch {
    return undefined;
  }
}

function comboConflictViolation(
  personality: PersonalityDefinition,
  media: MediaHandlingDefinition,
  highlight: "personality" | "mediaHandling",
): FieldViolation {
  const attrs = personalityMediaContradictions(personality, media);
  const labels = attrs.map((attribute) => ATTRIBUTE_LABELS[attribute]).join(", ");
  const mediaLabel = formatMediaHandlingLabel(media.styles);
  return {
    field: highlight,
    message: `${personality.id} is incompatible with ${mediaLabel} — conflicting ${labels || "attributes"} (bands do not overlap; this combo likely does not exist in-game)`,
  };
}

function bandMidpoint(band: { min: number; max: number }): number {
  return Math.round((band.min + band.max) / 2);
}

function resolveMediaDefinition(
  raw: string,
): MediaHandlingDefinition | undefined {
  const trimmed = raw.trim();
  if (!trimmed) return undefined;
  try {
    return findMediaHandling(catalog, parseMediaHandlingInput(trimmed));
  } catch {
    const matched = normalizeMatch(trimmed, mediaStyles);
    if (!matched) return undefined;
    try {
      return findMediaHandling(catalog, matched);
    } catch {
      return undefined;
    }
  }
}

/** Best-HAS media compatible with this personality (current regen roster). */
function bestCompatibleMediaForPersonality(
  personality: PersonalityDefinition,
  isRegen: boolean,
): MediaHandlingDefinition | undefined {
  const ranking = rankPersonalityMediaCombos(catalog, { isRegen });
  for (const entry of ranking.entries) {
    if (entry.personality !== personality.id) continue;
    const media = resolveMediaDefinition(entry.mediaHandling);
    if (media && isPersonalityMediaCompatible(personality, media)) return media;
  }
  return catalog.mediaHandling.find((media) =>
    isPersonalityMediaCompatible(personality, media),
  );
}

/** Best-HAS personality compatible with this media (current regen roster). */
function bestCompatiblePersonalityForMedia(
  media: MediaHandlingDefinition,
  isRegen: boolean,
): PersonalityDefinition | undefined {
  const mediaLabel = formatMediaHandlingLabel(media.styles);
  const ranking = rankPersonalityMediaCombos(catalog, { isRegen });
  for (const entry of ranking.entries) {
    if (entry.mediaHandling !== mediaLabel) continue;
    const personality = findPersonality(catalog, entry.personality);
    if (personality && isPersonalityMediaCompatible(personality, media)) {
      return personality;
    }
  }
  return catalog.personalities.find((personality) =>
    isPersonalityMediaCompatible(personality, media),
  );
}

/**
 * Second-click fix for a greyed-out combo: nudge Det/Lead/age/regen into range,
 * or swap the conflicting sibling to the best-HAS compatible partner.
 */
function applyComboConstraintFix(
  option: ComboOption,
  hooks: ComboBindHooks,
): boolean {
  if (hooks.isPersonality) {
    const personality = findPersonality(catalog, option.value);
    if (!personality) return false;

    for (const rule of personality.conditionals) {
      if (rule.kind === "regen_only" && !hooks.getIsRegen()) {
        setIsRegen(hooks.personalityFields.isRegenEl, true);
      }
      if (rule.kind === "min_age") {
        const age = hooks.getAge();
        if (age === undefined || age <= rule.age) {
          hooks.personalityFields.ageEl.value = String(rule.age + 1);
        }
      }
    }

    for (const attribute of ["determination", "leadership"] as const) {
      const value =
        attribute === "determination"
          ? hooks.getDetermination()
          : hooks.getLeadership();
      const band = personality.bands[attribute];
      if (!band || value === undefined) continue;
      if (value < band.min || value > band.max) {
        const el =
          attribute === "determination"
            ? hooks.personalityFields.determinationEl
            : hooks.personalityFields.leadershipEl;
        el.value = String(bandMidpoint(band));
      }
    }

    const media = hooks.getSelectedMedia();
    if (media && !isPersonalityMediaCompatible(personality, media)) {
      const replacement = bestCompatibleMediaForPersonality(
        personality,
        hooks.getIsRegen(),
      );
      hooks.siblingInput.value = replacement
        ? formatMediaHandlingLabel(replacement.styles)
        : "";
    }
    return true;
  }

  const media = resolveMediaDefinition(option.value);
  if (!media) return false;

  const personality = hooks.getSelectedPersonality();
  if (personality && !isPersonalityMediaCompatible(personality, media)) {
    const replacement = bestCompatiblePersonalityForMedia(
      media,
      hooks.getIsRegen(),
    );
    if (replacement) {
      hooks.siblingInput.value = replacement.id;
      applyPersonalityPrerequisites(replacement, hooks.personalityFields);
      for (const attribute of ["determination", "leadership"] as const) {
        const value =
          attribute === "determination"
            ? safeOptionalInt(hooks.personalityFields.determinationEl.value)
            : safeOptionalInt(hooks.personalityFields.leadershipEl.value);
        const band = replacement.bands[attribute];
        if (!band || value === undefined) continue;
        if (value < band.min || value > band.max) {
          const el =
            attribute === "determination"
              ? hooks.personalityFields.determinationEl
              : hooks.personalityFields.leadershipEl;
          el.value = String(bandMidpoint(band));
        }
      }
      for (const rule of replacement.conditionals) {
        if (rule.kind === "min_age") {
          const age = safeOptionalInt(hooks.personalityFields.ageEl.value);
          if (age !== undefined && age <= rule.age) {
            hooks.personalityFields.ageEl.value = String(rule.age + 1);
          }
        }
        if (rule.kind === "regen_only" && !hooks.getIsRegen()) {
          setIsRegen(hooks.personalityFields.isRegenEl, true);
        }
      }
    } else {
      hooks.siblingInput.value = "";
    }
  }
  return true;
}

function personalityComboOptions(
  isRegen: boolean = isRegenEl.checked,
  age: number | undefined = safeOptionalInt(ageEl.value),
  media: MediaHandlingDefinition | undefined = selectedMedia(),
  determination: number | undefined = safeOptionalInt(determinationEl.value),
  leadership: number | undefined = safeOptionalInt(leadershipEl.value),
): ComboOption[] {
  // isRegen is unused for greying — regen-only personalities auto-enable Regen on pick.
  void isRegen;
  const options: ComboOption[] = [];

  for (const personality of catalog.personalities) {
    // Canonical id only — aliases like "Light-Hearted" still resolve when typed,
    // but listing them beside "Light Hearted" looked like duplicates.
    const constraint = personalityListViolation(
      personality,
      age,
      media,
      determination,
      leadership,
    );
    options.push({
      value: personality.id,
      disabled: Boolean(constraint),
      ...(constraint
        ? { violation: constraint.violation, hint: constraint.hint }
        : {}),
    });
  }
  return options.sort((a, b) => a.value.localeCompare(b.value));
}

function mediaComboOptions(
  personality: PersonalityDefinition | undefined = selectedPersonality(),
): ComboOption[] {
  return catalog.mediaHandling
    .map((media) => {
      const value = formatMediaHandlingLabel(media.styles);
      const conflict =
        personality && !isPersonalityMediaCompatible(personality, media)
          ? comboConflictViolation(personality, media, "personality")
          : null;
      return {
        value,
        disabled: Boolean(conflict),
        ...(conflict
          ? { violation: conflict, hint: "Conflicts with personality" }
          : {}),
      };
    })
    .sort((a, b) => a.value.localeCompare(b.value));
}

function safeOptionalInt(raw: string): number | undefined {
  try {
    return parseOptionalInt(raw);
  } catch {
    return undefined;
  }
}

function clampToRange(
  value: number,
  range: { min: number; max: number },
): number {
  return Math.min(range.max, Math.max(range.min, value));
}

function enforceVisibleInputs(implied: ImpliedVisible): boolean {
  let changed = false;

  const det = parseOptionalInt(determinationEl.value);
  if (det !== undefined && implied.determination) {
    const next = clampToRange(det, implied.determination);
    if (next !== det) {
      determinationEl.value = String(next);
      changed = true;
    }
  }

  const lead = parseOptionalInt(leadershipEl.value);
  if (lead !== undefined && implied.leadership) {
    const next = clampToRange(lead, implied.leadership);
    if (next !== lead) {
      leadershipEl.value = String(next);
      changed = true;
    }
  }

  return changed;
}

function activeFormRoot(): HTMLElement {
  if (isProbeOpen()) {
    return probeMode === "compare" ? compareEl : checkerEl;
  }
  return document.body;
}

function clearFieldWarnings() {
  const root = activeFormRoot();
  for (const warn of root.querySelectorAll<HTMLElement>(".field-warn")) {
    warn.hidden = true;
    warn.setAttribute("aria-hidden", "true");
    warn.removeAttribute("title");
    warn.removeAttribute("aria-label");
  }
}

function showFieldWarnings(violations: FieldViolation[]) {
  clearFieldWarnings();
  if (violations.length === 0) return;

  const byField = new Map<string, string>();
  for (const violation of violations) {
    if (!byField.has(violation.field)) {
      byField.set(violation.field, violation.message);
    }
  }

  const root = activeFormRoot();
  for (const [field, message] of byField) {
    const host = root.querySelector<HTMLElement>(`[data-field="${field}"]`);
    const warn = host?.querySelector<HTMLElement>(".field-warn");
    if (!warn) continue;
    warn.hidden = false;
    warn.removeAttribute("aria-hidden");
    warn.title = message;
    warn.setAttribute("aria-label", message);
  }
}

/** Last personality×media×regen the Checker synced Det/Lea mids for. */
let lastCheckerSyncedComboKey = "";

function checkerComboKey(
  personalityId: string,
  mediaLabel: string,
  isRegen: boolean,
): string {
  return `${personalityId}\0${mediaLabel}\0${isRegen ? "N" : "R"}`;
}

function findCheckerRankEntry(
  personality: string | undefined,
  mediaHandling: string | undefined,
  isRegen: boolean,
): ComboRankEntry | undefined {
  if (!personality?.trim() || !mediaHandling?.trim()) return undefined;
  const person = findPersonality(catalog, personality);
  if (!person) return undefined;
  let mediaLabel: string;
  try {
    const media = findMediaHandling(catalog, mediaHandling);
    if (!media) return undefined;
    mediaLabel = formatMediaHandlingLabel(media.styles);
  } catch {
    return undefined;
  }

  // Same ladder as the Rank tool (unified REAL/NEWGEN list + current population filter).
  if (lastRankerEntries.length === 0) {
    renderPersonalityRanker();
  }
  const matches = lastRankerEntries.filter(
    (entry) =>
      entry.personality === person.id && entry.mediaHandling === mediaLabel,
  );
  if (matches.length === 0) return undefined;

  const preferredLabel = isRegen ? "NEWGEN" : "REAL";
  return (
    matches.find((entry) => entry.label === preferredLabel) ??
    matches.find((entry) => !entry.label) ??
    matches[0]
  );
}

function lookupComboRank(
  personality: string | undefined,
  mediaHandling: string | undefined,
  isRegen: boolean,
): number | undefined {
  return findCheckerRankEntry(personality, mediaHandling, isRegen)?.rank;
}

/**
 * When personality / media / regen actually change, load that ranked combo’s
 * Det/Lea catalog mids (or clear if the pair isn’t on the Rank ladder).
 */
function syncCheckerKnownAttrsFromComboIfChanged() {
  const person = selectedCheckPersonality();
  const media = selectedCheckMedia();
  if (!person || !media) return;

  const mediaLabel = formatMediaHandlingLabel(media.styles);
  const isRegen = checkIsRegenEl.checked;
  const key = checkerComboKey(person.id, mediaLabel, isRegen);
  if (key === lastCheckerSyncedComboKey) return;
  lastCheckerSyncedComboKey = key;

  if (!isPersonalityMediaCompatible(person, media)) {
    checkDeterminationEl.value = "";
    checkLeadershipEl.value = "";
    applyPersonalityPrerequisites(person, {
      ageEl: checkAgeEl,
      isRegenEl: checkIsRegenEl,
      determinationEl: checkDeterminationEl,
      leadershipEl: checkLeadershipEl,
    });
    syncQuickPicks();
    return;
  }

  const entry = findCheckerRankEntry(person.id, mediaLabel, isRegen);
  if (entry) {
    setKnownMidInput(checkDeterminationEl, entry.mids.determination);
    setKnownMidInput(checkLeadershipEl, entry.mids.leadership);
  } else {
    checkDeterminationEl.value = "";
    checkLeadershipEl.value = "";
  }

  applyPersonalityPrerequisites(person, {
    ageEl: checkAgeEl,
    isRegenEl: checkIsRegenEl,
    determinationEl: checkDeterminationEl,
    leadershipEl: checkLeadershipEl,
  });
  syncQuickPicks();
}

function commitCheckPersonalityOrMedia() {
  syncCheckerKnownAttrsFromComboIfChanged();
  runCheckEstimate();
}

function renderHaScore(
  attributes: EstimateResult["attributes"] | null,
  options?: { rank?: number; visible?: HaVisibleKnown },
) {
  const setRank = (rank: number | undefined) => {
    if (rank === undefined) {
      haRankEl.hidden = true;
      haRankEl.textContent = "";
      return;
    }
    haRankEl.hidden = false;
    haRankEl.textContent = `#${rank}`;
  };

  if (!attributes) {
    haScoreEl.hidden = true;
    haScoreEl.classList.remove("good", "bad");
    haScoreValueEl.textContent = "—";
    setRank(undefined);
    return;
  }
  const score = hiddenQualityScore(attributes, options?.visible);
  if (!Number.isFinite(score)) {
    haScoreEl.hidden = false;
    haScoreEl.classList.remove("good", "bad");
    haScoreValueEl.textContent = "—";
    setRank(undefined);
    haScoreEl.title =
      "HA index unavailable — personality / media bands conflict on at least one attribute";
    return;
  }
  const tone = hiddenQualityTone(
    score,
    catalogEliteHasFloor,
    catalogPoorHasCeiling,
  );
  haScoreEl.hidden = false;
  haScoreEl.classList.toggle("good", tone === "good");
  haScoreEl.classList.toggle("bad", tone === "bad");
  const rank = options?.rank;
  setRank(rank);
  const weightsTip = formatHaQualityWeightsTip(options?.visible);
  haScoreEl.title =
    rank !== undefined
      ? `Combo rank #${rank} · elite ≥ ${formatHaScore(catalogEliteHasFloor)} · poor ≤ ${formatHaScore(catalogPoorHasCeiling)} · ${weightsTip}`
      : `Elite ≥ ${formatHaScore(catalogEliteHasFloor)} · poor ≤ ${formatHaScore(catalogPoorHasCeiling)} · ${weightsTip}`;
  haScoreValueEl.textContent = formatHaScore(score);
}

function visibleKnownFromEstimate(result: EstimateResult): HaVisibleKnown | undefined {
  const visible: HaVisibleKnown = {};
  if (result.player.determination !== undefined) {
    visible.determination = result.player.determination;
  } else if (result.impliedVisible.determination) {
    const band = result.impliedVisible.determination;
    visible.determination = (band.min + band.max) / 2;
  }
  if (result.player.leadership !== undefined) {
    visible.leadership = result.player.leadership;
  } else if (result.impliedVisible.leadership) {
    const band = result.impliedVisible.leadership;
    visible.leadership = (band.min + band.max) / 2;
  }
  if (
    visible.determination === undefined &&
    visible.leadership === undefined
  ) {
    return undefined;
  }
  return visible;
}

function renderResult(result: EstimateResult) {
  attrBodyEl.replaceChildren();
  attrTableEl.removeAttribute("title");

  for (const attribute of MODELED_HAS_ATTRIBUTES) {
    const estimate = result.attributes[attribute];
    const unmodeled =
      Boolean(estimate.unmodeled) || isUnmodeledHiddenAttribute(attribute);
    const impossible = Boolean(
      !unmodeled && (estimate.impossible || estimate.min > estimate.max),
    );
    const tone = unmodeled
      ? "neutral"
      : impossible
        ? "bad"
        : attributeTone(attribute, estimate.midpoint);
    const row = document.createElement("tr");
    row.dataset.attribute = attribute;
    row.dataset.playerTone = tone;
    if (impossible) row.classList.add("is-impossible");
    if (unmodeled) row.classList.add("is-unmodeled");
    const mid =
      unmodeled || impossible
        ? "—"
        : Number.isInteger(estimate.midpoint)
          ? String(estimate.midpoint)
          : estimate.midpoint.toFixed(1);
    const range =
      unmodeled || impossible
        ? "—"
        : formatBandSpan({ min: estimate.min, max: estimate.max });
    const toneClass =
      mid === "—" ? "is-empty" : tone === "neutral" ? "" : tone;
    const exactClass = estimate.exact && !unmodeled ? "exact" : "";

    row.innerHTML = `
      <td>
        <span class="attr-name" title="${ATTRIBUTE_DESCRIPTIONS[attribute]}">
          ${ATTRIBUTE_LABELS[attribute]}
        </span>
      </td>
      <td class="attr-band fmt-band ${exactClass} ${toneClass}">${range}</td>
      <td class="attr-mid fmt-mid ${toneClass}">${mid}</td>
    `;
    if (unmodeled) {
      row.title = ATTRIBUTE_DESCRIPTIONS[attribute];
    } else if (impossible) {
      row.title =
        "Empty intersection (min > max) — this personality / media combo likely does not exist in-game";
    }
    attrBodyEl.append(row);
  }

  renderHaScore(result.attributes, {
    rank: lookupComboRank(
      result.player.personality,
      result.player.mediaHandling,
      Boolean(result.player.isRegen),
    ),
    visible: visibleKnownFromEstimate(result),
  });
  showFieldWarnings(result.violations);
}

/** Eligibility / known-input violations from the current form (no media required). */
function collectFieldViolations(): FieldViolation[] {
  const violations: FieldViolation[] = [];
  const personality = selectedPersonality();
  const media = selectedMedia();
  if (personality) {
    const block = personalityBlockReason(
      personality,
      isRegenEl.checked,
      safeOptionalInt(ageEl.value),
    );
    if (block) violations.push(block);
    const listConflict = personalityListViolation(
      personality,
      safeOptionalInt(ageEl.value),
      media,
      safeOptionalInt(determinationEl.value),
      safeOptionalInt(leadershipEl.value),
    );
    if (listConflict && listConflict.violation.field !== "mediaHandling") {
      violations.push(listConflict.violation);
    }
  }
  if (personality && media && !isPersonalityMediaCompatible(personality, media)) {
    const conflict = comboConflictViolation(
      personality,
      media,
      "mediaHandling",
    );
    violations.push(conflict);
    violations.push({ ...conflict, field: "personality" });
  }
  return violations;
}

function allPersonalityNames(): string[] {
  const names: string[] = [];
  for (const personality of catalog.personalities) {
    names.push(personality.id);
    for (const alias of personality.aliases) {
      if (alias !== personality.id) names.push(alias);
    }
  }
  return names;
}

/** Pending combo blur timers (personality/media); cleared when leaving a card. */
const comboBlurTimers = new Set<number>();

type BoundComboController = {
  input: HTMLInputElement;
  listEl: HTMLUListElement;
  contains: (node: Node) => boolean;
  closeAndLock: () => void;
};

const boundComboControllers: BoundComboController[] = [];

/** Close open personality/media lists and lock the current text into a selection. */
function closeAndLockOpenCombos(except?: BoundComboController) {
  for (const combo of boundComboControllers) {
    if (combo === except) continue;
    combo.closeAndLock();
  }
}

document.addEventListener(
  "pointerdown",
  (event) => {
    const target = event.target;
    if (!(target instanceof Node)) return;
    for (const combo of boundComboControllers) {
      if (combo.contains(target)) continue;
      combo.closeAndLock();
    }
  },
  true,
);

/** Commit in-flight edits to the current active card before switching away. */
function commitActiveCardBeforeSwitch() {
  window.clearTimeout(historyTimer);
  window.clearTimeout(labelSaveTimer);
  window.clearTimeout(saveTimer);
  for (const timer of comboBlurTimers) window.clearTimeout(timer);
  comboBlurTimers.clear();
  closeAndLockOpenCombos();
  if (pendingHistory) flushHistory();
  commitLabelFormToActive();
}

type ComboBindHooks = {
  onCommit: () => void;
  isPersonality: boolean;
  siblingInput: HTMLInputElement;
  siblingList: HTMLUListElement;
  getIsRegen: () => boolean;
  getAge: () => number | undefined;
  getSelectedMedia: () => MediaHandlingDefinition | undefined;
  getSelectedPersonality: () => PersonalityDefinition | undefined;
  getDetermination: () => number | undefined;
  getLeadership: () => number | undefined;
  personalityFields: PersonalityFieldSet;
};

function bindCombo(
  input: HTMLInputElement,
  listEl: HTMLUListElement,
  getOptions: () => ComboOption[],
  hooks: ComboBindHooks,
) {
  let activeIndex = -1;
  let currentOptions: ComboOption[] = [];
  let constraintFlash: { value: string; hint: string } | null = null;

  const clearConstraintFlash = () => {
    const prior = comboFlashTimers.get(listEl);
    if (prior !== undefined) window.clearTimeout(prior);
    comboFlashTimers.delete(listEl);
    constraintFlash = null;
  };

  const showConstraintFlash = (value: string, hint: string) => {
    constraintFlash = { value, hint };
    const prior = comboFlashTimers.get(listEl);
    if (prior !== undefined) window.clearTimeout(prior);
    const timer = window.setTimeout(() => {
      constraintFlash = null;
      comboFlashTimers.delete(listEl);
      if (!listEl.hidden) refresh(true);
    }, 4200);
    comboFlashTimers.set(listEl, timer);
  };

  const close = () => {
    listEl.hidden = true;
    clearComboListAnchor(listEl);
    activeIndex = -1;
    input.setAttribute("aria-expanded", "false");
  };

  let blurTimer: number | null = null;
  let lockingSelection = false;

  const clearBlurTimer = () => {
    if (blurTimer === null) return;
    window.clearTimeout(blurTimer);
    comboBlurTimers.delete(blurTimer);
    blurTimer = null;
  };

  const pick = (option: ComboOption) => {
    if (option.disabled) {
      if (!option.violation) return;
      // First click: show why. Second click on the same option: auto-fix & pick.
      if (constraintFlash?.value === option.value) {
        if (applyComboConstraintFix(option, hooks)) {
          clearConstraintFlash();
          input.value = option.value;
          if (hooks.isPersonality) {
            const personality = findPersonality(catalog, option.value);
            if (personality) {
              applyPersonalityPrerequisites(
                personality,
                hooks.personalityFields,
              );
            }
          }
          close();
          clearFieldWarnings();
          hooks.onCommit();
          if (!hooks.siblingList.hidden) {
            hooks.siblingInput.dispatchEvent(new Event("input"));
          }
          return;
        }
      }
      showConstraintFlash(
        option.value,
        `${option.hint ?? option.violation.message} · click again to auto-fix`,
      );
      showFieldWarnings([option.violation]);
      refresh(true);
      input.focus();
      return;
    }
    clearConstraintFlash();
    input.value = option.value;
    if (hooks.isPersonality) {
      const personality = findPersonality(catalog, option.value);
      if (personality) applyPersonalityPrerequisites(personality, hooks.personalityFields);
    }
    close();
    clearFieldWarnings();
    // Always commit (Checker syncs Det/Lea from the ranked combo). Refresh an
    // open sibling list afterward — previously we returned early and skipped commit.
    hooks.onCommit();
    if (!hooks.siblingList.hidden) {
      hooks.siblingInput.dispatchEvent(new Event("input"));
    }
  };

  const refresh = (keepIndex = false) => {
    currentOptions = filterOptions(input.value, getOptions());
    if (!keepIndex) activeIndex = currentOptions.length > 0 ? 0 : -1;
    if (activeIndex >= currentOptions.length) {
      activeIndex = currentOptions.length - 1;
    }
    renderComboList(
      listEl,
      currentOptions,
      activeIndex,
      pick,
      constraintFlash,
    );
    input.setAttribute("aria-expanded", String(!listEl.hidden));
    if (activeIndex >= 0) {
      input.setAttribute(
        "aria-activedescendant",
        `${listEl.id}-opt-${activeIndex}`,
      );
    } else {
      input.removeAttribute("aria-activedescendant");
    }
  };

  const resolveOnBlur = () => {
    const raw = input.value.trim();
    if (!raw) {
      hooks.onCommit();
      return;
    }

    if (hooks.isPersonality) {
      const personality = findPersonality(catalog, raw);
      if (personality) {
        if (raw !== personality.id) input.value = personality.id;
        const conflict = personalityListViolation(
          personality,
          hooks.getAge(),
          hooks.getSelectedMedia(),
          hooks.getDetermination(),
          hooks.getLeadership(),
        );
        if (conflict) {
          // Keep the menu closed on blur — refreshing here flashed the list
          // after Det/Lea/Age quick-picks (blur → resolve → reopen).
          constraintFlash = {
            value: personality.id,
            hint: conflict.hint,
          };
          showFieldWarnings([conflict.violation]);
          hooks.onCommit();
          return;
        }
        clearConstraintFlash();
        applyPersonalityPrerequisites(personality, hooks.personalityFields);
        clearFieldWarnings();
        hooks.onCommit();
        return;
      }
      hooks.onCommit();
      return;
    }

    const matched = normalizeMatch(raw, mediaStyles);
    if (matched) {
      if (matched !== input.value) input.value = matched;
      const media = hooks.getSelectedMedia();
      const personality = hooks.getSelectedPersonality();
      if (
        personality &&
        media &&
        !isPersonalityMediaCompatible(personality, media)
      ) {
        const conflict = comboConflictViolation(
          personality,
          media,
          "personality",
        );
        constraintFlash = {
          value: matched,
          hint: "Conflicts with personality",
        };
        showFieldWarnings([conflict]);
      }
      hooks.onCommit();
      return;
    }
    hooks.onCommit();
  };

  const closeAndLock = () => {
    if (lockingSelection) return;
    const shouldResolve =
      !listEl.hidden || document.activeElement === input;
    lockingSelection = true;
    try {
      clearBlurTimer();
      close();
      if (shouldResolve) resolveOnBlur();
      if (document.activeElement === input) input.blur();
      clearBlurTimer();
    } finally {
      lockingSelection = false;
    }
  };

  boundComboControllers.push({
    input,
    listEl,
    contains: (node) => input.contains(node) || listEl.contains(node),
    closeAndLock,
  });

  input.addEventListener("focus", () => refresh());
  input.addEventListener("input", () => {
    refresh();
    hooks.onCommit();
  });
  input.addEventListener("blur", () => {
    if (lockingSelection) return;
    clearBlurTimer();
    const timer = window.setTimeout(() => {
      if (blurTimer === timer) blurTimer = null;
      comboBlurTimers.delete(timer);
      close();
      resolveOnBlur();
    }, 120);
    blurTimer = timer;
    comboBlurTimers.add(timer);
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      close();
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (listEl.hidden) refresh();
      if (currentOptions.length === 0) return;
      activeIndex = Math.min(activeIndex + 1, currentOptions.length - 1);
      refresh(true);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      if (listEl.hidden) refresh();
      if (currentOptions.length === 0) return;
      activeIndex = Math.max(activeIndex - 1, 0);
      refresh(true);
      return;
    }

    if (event.key === "Enter") {
      event.preventDefault();
      if (!listEl.hidden && activeIndex >= 0 && currentOptions[activeIndex]) {
        pick(currentOptions[activeIndex]!);
        return;
      }
      const pool = hooks.isPersonality ? allPersonalityNames() : mediaStyles;
      const matched = normalizeMatch(input.value, pool);
      if (!matched) return;
      const option = getOptions().find((item) => item.value === matched);
      if (option) pick(option);
    }
  });
}

function syncQuickPicks() {
  for (const group of document.querySelectorAll<HTMLElement>(".quick-picks")) {
    const target = group.dataset.target;
    if (!target) continue;
    const form = group.closest("form");
    const input =
      form?.querySelector<HTMLInputElement>(`#${target}`) ??
      document.querySelector<HTMLInputElement>(`#${target}`);
    if (!input) continue;
    const current = input.value.trim();

    let minAge: number | undefined;
    const personalityInput =
      form?.querySelector<HTMLInputElement>("#personality") ??
      form?.querySelector<HTMLInputElement>("#check-personality") ??
      personalityEl;
    const selected = findPersonality(catalog, personalityInput.value.trim());
    if (selected) {
      for (const rule of selected.conditionals) {
        if (rule.kind === "min_age") minAge = rule.age;
      }
    }

    const impliedKey =
      target === "determination" || target === "check-determination"
        ? "determination"
        : target === "leadership" || target === "check-leadership"
          ? "leadership"
          : undefined;
    const impliedSource =
      form?.id === "check-form" ? lastCheckImpliedVisible : lastImpliedVisible;
    const implied = impliedKey ? impliedSource[impliedKey] : undefined;

    for (const button of group.querySelectorAll("button")) {
      const raw = button.dataset.value ?? "";
      button.classList.toggle("active", raw === current);
      const value = Number(raw);
      if (!Number.isFinite(value)) {
        button.disabled = true;
        continue;
      }
      if (
        (target === "age" || target === "check-age") &&
        minAge !== undefined &&
        value <= minAge
      ) {
        button.disabled = true;
        continue;
      }
      if (implied && (value < implied.min || value > implied.max)) {
        button.disabled = true;
        continue;
      }
      button.disabled = false;
    }
  }
}

function readSignals(): HistorySignals {
  const determination = parseOptionalInt(determinationEl.value);
  const leadership = parseOptionalInt(leadershipEl.value);
  const age = parseOptionalInt(ageEl.value);
  assertAttrInScale("Determination", determination);
  assertAttrInScale("Leadership", leadership);

  const personalityMatch = findPersonality(catalog, personalityEl.value);
  const personality = personalityMatch?.id ?? personalityEl.value.trim();
  const mediaHandling =
    normalizeMatch(mediaEl.value, mediaStyles) ?? mediaEl.value.trim();

  return {
    personality,
    mediaHandling,
    ...(determination !== undefined ? { determination } : {}),
    ...(leadership !== undefined ? { leadership } : {}),
    ...(age !== undefined ? { age } : {}),
    isRegen: isRegenEl.checked,
  };
}

function applySignals(entry: PlayerEntry) {
  suppressHistory = true;
  personalityEl.value = entry.signals.personality;
  mediaEl.value = entry.signals.mediaHandling;
  determinationEl.value =
    entry.signals.determination !== undefined
      ? String(entry.signals.determination)
      : "";
  leadershipEl.value =
    entry.signals.leadership !== undefined
      ? String(entry.signals.leadership)
      : "";
  ageEl.value = entry.signals.age !== undefined ? String(entry.signals.age) : "";
  isRegenEl.checked = entry.signals.isRegen;
  syncRegenChip(isRegenEl);
  suppressHistory = false;
  syncQuickPicks();
}

/** Always two decimals so near-ties stay visually distinct. */
function formatHaScore(score: number): string {
  return score.toFixed(2);
}

function formatHaMid(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

/** Per-entry HAS tip: weights, plugged-in calculation, floor, and sort order. */
function rankerEntryTitle(entry: ComboRankEntry): string {
  const w = HA_QUALITY_WEIGHTS;
  const vw = HA_VISIBLE_QUALITY_WEIGHTS;
  const m = entry.mids;
  const visible: HaVisibleKnown = {
    ...(m.determination !== null ? { determination: m.determination } : {}),
    ...(m.leadership !== null ? { leadership: m.leadership } : {}),
  };
  const sum = haQualityWeightSum(
    Object.keys(visible).length > 0 ? visible : undefined,
  );
  const pro = formatHaMid(m.professionalism);
  const pre = formatHaMid(m.pressure);
  const amb = formatHaMid(m.ambition);
  const tem = formatHaMid(m.temperament);
  const loy = formatHaMid(m.loyalty);
  const spo = formatHaMid(m.sportsmanship);
  const con = formatHaMid(m.controversy);
  const conInv = formatHaMid(invertControversy(m.controversy));
  const has = formatHaScore(entry.haScore);
  const floor = formatHaScore(entry.floorScore);
  // Same weighted presentation order as the attributes probe / rank columns.
  const parts: string[] = [];
  if (m.determination !== null) {
    parts.push(`${vw.determination}×Det ${formatHaMid(m.determination)}`);
  }
  parts.push(
    `${w.professionalism}×Pro ${pro}`,
    `${w.pressure}×Pre ${pre}`,
    `${w.ambition}×Amb ${amb}`,
    `${w.temperament}×Tem ${tem}`,
  );
  if (m.leadership !== null) {
    parts.push(`${vw.leadership}×Lea ${formatHaMid(m.leadership)}`);
  }
  parts.push(
    `${w.loyalty}×Loy ${loy}`,
    `${w.sportsmanship}×Spo ${spo}`,
    `${w.controversy}×(21−Con ${con}→${conInv})`,
  );
  return [
    `Weights: ${formatHaQualityWeightsTip(
      Object.keys(visible).length > 0 ? visible : undefined,
    )}`,
    `HAS ${has} = (${parts.join(" + ")}) ÷ ${sum}`,
    `Floor ${floor} (same weights on band mins / Con max` +
      (m.determination !== null || m.leadership !== null
        ? "; known Det/Lead mins"
        : "") +
      `)`,
    `Rank: HAS → floor → name`,
  ].join("\n");
}

function createHaBadge(score: number, tone: string): HTMLElement {
  const badge = document.createElement("span");
  badge.className = tone === "neutral" ? "ranker-ha" : `ranker-ha ${tone}`;
  const icon = document.createElement("span");
  icon.className = "ha-score-icon";
  icon.setAttribute("aria-hidden", "true");
  const value = document.createElement("span");
  value.textContent = formatHaScore(score);
  badge.append(icon, value);
  return badge;
}

/** Attr breakdown tip for narrow density — mid then band on each line. */
function haAttrsTipFromRow(row: HTMLTableRowElement): string {
  const cells = row.querySelectorAll<HTMLElement>("td.ranker-col-mid");
  const lines: string[] = ["     mid     band"];
  for (let i = 0; i < RANK_ATTR_COLS.length; i += 1) {
    const col = RANK_ATTR_COLS[i]!;
    const cell = cells[i];
    const mid = cell?.dataset.midText ?? "—";
    const band = cell?.dataset.bandText ?? "—";
    lines.push(`${col.header.padEnd(3, " ")}  ${mid.padStart(4, " ")}  ${band}`);
  }
  return lines.join("\n");
}

function wireRankerHaAttrsTip(
  badge: HTMLElement,
  row: HTMLTableRowElement,
): void {
  badge.classList.add("ranker-ha-tip");
  badge.tabIndex = 0;
  badge.setAttribute("role", "button");
  badge.setAttribute(
    "aria-label",
    `HAS ${badge.textContent?.trim() ?? ""}. Show hidden attributes.`,
  );

  const show = () => {
    // Attr tip is for narrow only — mid/wide already show the columns.
    if (parseRankerDensity(rankEl.dataset.density) !== "narrow") return;
    showMetricTip(badge, haAttrsTipFromRow(row));
  };

  badge.addEventListener("mouseenter", show);
  badge.addEventListener("mouseleave", () => {
    if (metricTipEl?.dataset.pinned === "1") return;
    hideMetricTip();
  });
  badge.addEventListener("focus", show);
  badge.addEventListener("blur", () => {
    if (metricTipEl?.dataset.pinned === "1") return;
    hideMetricTip();
  });
  badge.addEventListener("click", (event) => {
    if (parseRankerDensity(rankEl.dataset.density) !== "narrow") return;
    event.preventDefault();
    event.stopPropagation();
    const tip = ensureMetricTip();
    const tipText = haAttrsTipFromRow(row);
    if (!tip.hidden && tip.dataset.pinned === "1" && tip.textContent === tipText) {
      hideMetricTip();
      return;
    }
    showMetricTip(badge, tipText);
    tip.dataset.pinned = "1";
  });
}

function createPopulationLabel(
  label: ComboRankEntry["label"],
): HTMLElement {
  const el = document.createElement("span");
  if (!label) {
    el.className = "ranker-pop is-empty";
    el.textContent = "";
    return el;
  }
  el.className = `ranker-pop is-${label.toLowerCase()}`;
  el.textContent = label;
  return el;
}

/** Pin REAL/NEWGEN to the card corner so meta HA stays centered. */
function setPodiumPopulationLabel(
  card: HTMLElement,
  label: ComboRankEntry["label"],
): void {
  card.querySelector(":scope > .ranker-pop")?.remove();
  if (!label) return;
  card.append(createPopulationLabel(label));
}

/** Keep NEWGEN / REAL chip chrome in sync with a hidden isRegen checkbox. */
function syncRegenChip(checkbox: HTMLInputElement) {
  const chip =
    checkbox
      .closest(".regen-chip-field")
      ?.querySelector<HTMLButtonElement>(".regen-chip-toggle") ??
    document.querySelector<HTMLButtonElement>(
      `button.regen-chip-toggle[data-regen-for="${checkbox.id}"]`,
    );
  if (!chip) return;
  const isRegen = checkbox.checked;
  chip.textContent = isRegen ? "NEWGEN" : "REAL";
  chip.classList.toggle("is-newgen", isRegen);
  chip.classList.toggle("is-real", !isRegen);
  chip.setAttribute("aria-pressed", String(isRegen));
  chip.setAttribute(
    "aria-label",
    isRegen ? "NEWGEN — click for REAL" : "REAL — click for NEWGEN",
  );
  chip.title = isRegen ? "Click for REAL" : "Click for NEWGEN";
}

function setIsRegen(checkbox: HTMLInputElement, value: boolean) {
  checkbox.checked = value;
  syncRegenChip(checkbox);
}

function bindRegenChip(
  checkbox: HTMLInputElement,
  chip: HTMLButtonElement,
  onToggle?: () => void,
) {
  if (checkbox.id) chip.dataset.regenFor = checkbox.id;
  syncRegenChip(checkbox);
  chip.addEventListener("click", () => {
    setIsRegen(checkbox, !checkbox.checked);
    checkbox.dispatchEvent(new Event("input", { bubbles: true }));
    checkbox.dispatchEvent(new Event("change", { bubbles: true }));
    onToggle?.();
  });
}

type RankAttrCol = {
  key: (typeof CHECKER_TABLE_ATTRIBUTES)[number];
  header: string;
  title: string;
  /**
   * Minimum density that includes this column.
   * Column order matches {@link CHECKER_TABLE_ATTRIBUTES} (weight order).
   * mid  → Pro Pre Amb Tem Loy Spo Con
   * wide → also Det / Lea in their weighted slots
   */
  showFrom: "mid" | "wide";
  /** Attribute used for good/bad paint from midpoint. */
  toneAttr?: TrackedAttribute | null;
};

/** Probe-weighted HA columns (Det before Pro; Lea after Tem). */
const RANK_ATTR_COL_META: Record<
  (typeof CHECKER_TABLE_ATTRIBUTES)[number],
  { header: string; title: string; showFrom: "mid" | "wide" }
> = {
  determination: { header: "DET", title: "Determination", showFrom: "wide" },
  professionalism: { header: "PRO", title: "Professionalism", showFrom: "mid" },
  pressure: { header: "PRE", title: "Pressure", showFrom: "mid" },
  ambition: { header: "AMB", title: "Ambition", showFrom: "mid" },
  temperament: { header: "TEM", title: "Temperament", showFrom: "mid" },
  leadership: { header: "LEA", title: "Leadership", showFrom: "wide" },
  loyalty: { header: "LOY", title: "Loyalty", showFrom: "mid" },
  sportsmanship: { header: "SPO", title: "Sportsmanship", showFrom: "mid" },
  controversy: { header: "CON", title: "Controversy", showFrom: "mid" },
};

const RANK_ATTR_COLS: RankAttrCol[] = CHECKER_TABLE_ATTRIBUTES.map((key) => ({
  key,
  header: RANK_ATTR_COL_META[key].header,
  title: RANK_ATTR_COL_META[key].title,
  showFrom: RANK_ATTR_COL_META[key].showFrom,
  toneAttr: key,
}));

/** Modeled HAS attrs for Personalities / Attributes HA tables (Imp omitted). */
const MODELED_HAS_ATTRIBUTES = HAS_ATTRIBUTES.filter(
  (attr) => !isUnmodeledHiddenAttribute(attr),
);

type RankerDensity = "narrow" | "mid" | "wide";

function parseRankerDensity(value: string | undefined): RankerDensity {
  if (value === "mid" || value === "wide") return value;
  return "narrow";
}

function attrColClass(col: RankAttrCol, valueMode: "mid" | "band"): string {
  const band = valueMode === "band" ? " is-band" : "";
  return `ranker-col-mid ranker-attr-${col.showFrom}${band}`;
}

const RANK_POPULATION_CYCLE: RankPopulationMode[] = ["mixed", "real", "newgen"];

function populationFilterLabel(mode: RankPopulationMode): string {
  if (mode === "real") return "REAL";
  if (mode === "newgen") return "NEWGEN";
  return "MIXED";
}

function cycleRankerPopulation(): RankPopulationMode {
  const index = RANK_POPULATION_CYCLE.indexOf(rankerPopulation);
  return RANK_POPULATION_CYCLE[(index + 1) % RANK_POPULATION_CYCLE.length]!;
}

function compareNullableMid(
  a: number | null,
  b: number | null,
  asc: boolean,
): number {
  const aNull = a === null || !Number.isFinite(a);
  const bNull = b === null || !Number.isFinite(b);
  if (aNull && bNull) return 0;
  if (aNull) return 1; // nulls last
  if (bNull) return -1;
  const dir = asc ? 1 : -1;
  if (a! < b!) return -1 * dir;
  if (a! > b!) return 1 * dir;
  return 0;
}

function sortRankerEntries(entries: ComboRankEntry[]): ComboRankEntry[] {
  const asc = rankerSortAsc;
  const key = rankerSortKey;
  return [...entries].sort((a, b) => {
    if (key === "has") {
      const dir = asc ? 1 : -1;
      if (a.haScore !== b.haScore) {
        return (a.haScore < b.haScore ? -1 : 1) * dir;
      }
      return a.rank - b.rank;
    }
    const cmp = compareNullableMid(a.mids[key], b.mids[key], asc);
    if (cmp !== 0) return cmp;
    if (a.haScore !== b.haScore) return b.haScore - a.haScore;
    return a.rank - b.rank;
  });
}

/** Click: new key → desc; same key → asc; then clear to default HAS desc. */
function cycleRankerSort(key: RankerSortKey) {
  if (rankerSortKey !== key) {
    rankerSortKey = key;
    rankerSortAsc = false;
  } else if (!rankerSortAsc) {
    rankerSortAsc = true;
  } else {
    rankerSortKey = "has";
    rankerSortAsc = false;
  }
}

function isRankerAttrSorted(key: keyof ComboRankEntry["mids"]): boolean {
  return rankerSortKey === key;
}

function applyRankerSort() {
  refreshRankerListView();
}

function refreshRankerListView() {
  if (!rankerListEl) return;
  const filtered = lastRankerEntries.filter(entryPassesRankerFilters);
  const scrollTop = rankerListEl.scrollTop;
  renderRankerPodium(filtered);
  renderRankerList(sortRankerEntries(filtered));
  rankerListEl.scrollTop = scrollTop;
  refreshRankerFind({ keepIndex: true });
  scheduleRankerDensitySync();
}

const RANKER_FILTER_NUMERIC_OPS: { value: RankerFilterOp; label: string }[] = [
  { value: "gte", label: "Is at least" },
  { value: "lte", label: "Is at most" },
  { value: "eq", label: "Is" },
  { value: "neq", label: "Is not" },
];

const RANKER_FILTER_TEXT_OPS: { value: RankerFilterOp; label: string }[] = [
  { value: "eq", label: "Is" },
  { value: "neq", label: "Is not" },
];

function isRankerTextFilterKey(key: RankerFilterKey): key is RankerTextFilterKey {
  return key === "personality" || key === "mediaHandling" || key === "player";
}

function rankerFilterKeyLabel(key: RankerFilterKey): string {
  if (key === "has") return "HAS";
  if (key === "personality") return "Personality";
  if (key === "mediaHandling") return "Media handling";
  if (key === "player") return "Player";
  const col = RANK_ATTR_COLS.find((c) => c.key === key);
  return col?.title ?? key;
}

function defaultRankerFilterValue(key: RankerFilterKey): number | string {
  if (key === "personality") {
    return catalog.personalities[0]?.id ?? "";
  }
  if (key === "mediaHandling") {
    const media = catalog.mediaHandling[0];
    return media ? formatMediaHandlingLabel(media.styles) : "";
  }
  if (key === "player") return "NEWGEN";
  return key === "has" ? 12 : 10;
}

function newRankerFilter(): RankerFilter {
  rankerFilterSeq += 1;
  return {
    id: `rf-${rankerFilterSeq}`,
    key: "personality",
    op: "eq",
    value: defaultRankerFilterValue("personality"),
  };
}

function entryFilterMid(
  entry: ComboRankEntry,
  key: RankerNumericFilterKey,
): number | null {
  if (key === "has") return entry.haScore;
  const mid = entry.mids[key];
  return mid === null || !Number.isFinite(mid) ? null : mid;
}

function entryFilterBand(
  entry: ComboRankEntry,
  key: RankerNumericFilterKey,
): { min: number; max: number } | null {
  if (key === "has") {
    const score = entry.haScore;
    if (!Number.isFinite(score)) return null;
    return { min: score, max: score };
  }
  return entry.bands[key];
}

/** Mid view: compare against midpoint. */
function matchRankerFilterMid(
  mid: number | null,
  op: RankerFilterOp,
  target: number,
): boolean {
  if (mid === null) return false;
  switch (op) {
    case "gte":
      return mid >= target;
    case "lte":
      return mid <= target;
    case "eq":
      return Math.abs(mid - target) < 0.05;
    case "neq":
      return Math.abs(mid - target) >= 0.05;
  }
}

/**
 * Band containment for a player coordinate (`Is` / `Is not`):
 * - no band / full 1–20 → unconstrained (accepts any exact value)
 * - otherwise true when target ∈ [min, max]
 */
function matchRankerFilterBand(
  band: { min: number; max: number } | null,
  op: RankerFilterOp,
  target: number,
): boolean {
  const unconstrained =
    !band ||
    (band.min === FULL_RANGE.min && band.max === FULL_RANGE.max);
  switch (op) {
    case "gte":
      if (unconstrained) return false;
      return band!.min >= target;
    case "lte":
      if (unconstrained) return false;
      return band!.max <= target;
    case "eq":
      // Player Det IS 18 → which combos’ Det band contain 18?
      if (unconstrained) return true;
      return band!.min <= target && target <= band!.max;
    case "neq":
      if (unconstrained) return false;
      return target < band!.min || target > band!.max;
  }
}

/**
 * Population label on mixed list:
 * - NEWGEN/REAL chip → that roster only
 * - unlabeled → available for both (matches either Player is…)
 */
function matchRankerPlayerFilter(
  entry: ComboRankEntry,
  op: RankerFilterOp,
  target: string,
): boolean {
  const want = target === "REAL" ? "REAL" : "NEWGEN";
  const label = entry.label ?? null;
  const isMatch =
    label === null ? true : label === want;
  return op === "eq" ? isMatch : !isMatch;
}

function matchRankerTextFilter(
  entry: ComboRankEntry,
  filter: RankerFilter,
): boolean {
  const target = String(filter.value);
  if (filter.key === "player") {
    return matchRankerPlayerFilter(entry, filter.op, target);
  }
  const actual =
    filter.key === "personality" ? entry.personality : entry.mediaHandling;
  const equal =
    actual.localeCompare(target, undefined, { sensitivity: "accent" }) === 0;
  return filter.op === "eq" ? equal : !equal;
}

function matchRankerFilter(
  entry: ComboRankEntry,
  filter: RankerFilter,
): boolean {
  if (isRankerTextFilterKey(filter.key)) {
    return matchRankerTextFilter(entry, filter);
  }
  const numericKey = filter.key;
  const target = typeof filter.value === "number" ? filter.value : Number(filter.value);
  if (!Number.isFinite(target)) return false;

  // Player-coordinate filters: Is / Is not always means band contains the value.
  // Mid display mode is for ranking/display; it must not redefine "Det IS 18".
  const playerCoordinateIs =
    numericKey !== "has" && (filter.op === "eq" || filter.op === "neq");
  if (playerCoordinateIs || rankerValueMode === "band") {
    return matchRankerFilterBand(
      entryFilterBand(entry, numericKey),
      filter.op,
      target,
    );
  }
  return matchRankerFilterMid(
    entryFilterMid(entry, numericKey),
    filter.op,
    target,
  );
}

/** Left-to-right evaluation using between-row AND/OR joins. */
function entryPassesRankerFilters(entry: ComboRankEntry): boolean {
  if (rankerFilters.length === 0) return true;
  let acc = matchRankerFilter(entry, rankerFilters[0]!);
  for (let i = 1; i < rankerFilters.length; i += 1) {
    const next = matchRankerFilter(entry, rankerFilters[i]!);
    const join = rankerFilterJoins[i - 1] ?? "and";
    acc = join === "and" ? acc && next : acc || next;
  }
  return acc;
}

function fillSelect(
  select: HTMLSelectElement,
  options: { value: string; label: string }[],
  selected: string,
) {
  select.replaceChildren();
  for (const opt of options) {
    const el = document.createElement("option");
    el.value = opt.value;
    el.textContent = opt.label;
    if (opt.value === selected) el.selected = true;
    select.append(el);
  }
}

function syncRankerFilterCount() {
  const n = rankerFilters.length;
  if (!rankerFilterCountEl) return;
  if (n === 0) {
    rankerFilterCountEl.hidden = true;
    rankerFilterCountEl.textContent = "";
    rankerFilterToggleEl?.removeAttribute("data-active");
    return;
  }
  rankerFilterCountEl.hidden = false;
  rankerFilterCountEl.textContent = String(n);
  rankerFilterToggleEl?.setAttribute("data-active", "true");
}

function setRankerFilterPopoverOpen(open: boolean) {
  if (!rankerFilterPopoverEl || !rankerFilterToggleEl) return;
  rankerFilterPopoverEl.hidden = !open;
  rankerFilterToggleEl.setAttribute("aria-expanded", String(open));
}

function renderRankerFilters() {
  if (!rankerFilterRowsEl) return;
  rankerFilterRowsEl.replaceChildren();
  syncRankerFilterCount();

  const keyOptions = [
    { value: "personality", label: "Personality" },
    { value: "mediaHandling", label: "Media handling" },
    { value: "player", label: "Player" },
    ...RANK_ATTR_COLS.map((col) => ({
      value: col.key,
      label: col.title,
    })),
    { value: "has", label: "HAS" },
  ];

  const personalityOptions = [...catalog.personalities]
    .map((p) => p.id)
    .sort((a, b) => a.localeCompare(b))
    .map((id) => ({ value: id, label: id }));
  const mediaOptions = catalog.mediaHandling
    .map((media) => formatMediaHandlingLabel(media.styles))
    .sort((a, b) => a.localeCompare(b))
    .map((label) => ({ value: label, label }));
  const playerOptions = [
    { value: "NEWGEN", label: "Regen / newgen" },
    { value: "REAL", label: "Real" },
  ];
  const numericValueOptions = Array.from({ length: 20 }, (_, i) => {
    const n = i + 1;
    return { value: String(n), label: String(n) };
  });

  if (rankerFilters.length === 0) {
    const empty = document.createElement("p");
    empty.className = "ranker-filter-empty";
    empty.textContent = "No filters yet.";
    rankerFilterRowsEl.append(empty);
    return;
  }

  rankerFilters.forEach((filter, index) => {
    if (index > 0) {
      const joinWrap = document.createElement("div");
      joinWrap.className = "ranker-filter-join";
      const joinBtn = document.createElement("button");
      joinBtn.type = "button";
      joinBtn.className = "ranker-filter-join-btn";
      const join = rankerFilterJoins[index - 1] ?? "and";
      joinBtn.textContent = join.toUpperCase();
      joinBtn.setAttribute(
        "aria-label",
        `Join filters with ${join.toUpperCase()}. Click to toggle AND/OR.`,
      );
      joinBtn.addEventListener("click", () => {
        rankerFilterJoins[index - 1] = join === "and" ? "or" : "and";
        renderRankerFilters();
        refreshRankerListView();
      });
      joinWrap.append(joinBtn);
      rankerFilterRowsEl.append(joinWrap);
    }

    const textKey = isRankerTextFilterKey(filter.key);
    const row = document.createElement("div");
    row.className = "ranker-filter-row";
    row.dataset.filterId = filter.id;
    if (textKey) row.dataset.filterKind = "text";

    const keySel = document.createElement("select");
    keySel.className = "ranker-filter-key";
    keySel.setAttribute("aria-label", "Filter field");
    fillSelect(keySel, keyOptions, filter.key);

    const opSel = document.createElement("select");
    opSel.className = "ranker-filter-op";
    opSel.setAttribute("aria-label", "Filter comparison");
    const opOptions = (textKey ? RANKER_FILTER_TEXT_OPS : RANKER_FILTER_NUMERIC_OPS).map(
      (op) => ({ value: op.value, label: op.label }),
    );
    const opValue =
      textKey && (filter.op === "gte" || filter.op === "lte") ? "eq" : filter.op;
    if (opValue !== filter.op) filter.op = opValue;
    fillSelect(opSel, opOptions, filter.op);

    const valSel = document.createElement("select");
    valSel.className = "ranker-filter-value";
    valSel.setAttribute("aria-label", "Filter value");
    const valueOptions =
      filter.key === "personality"
        ? personalityOptions
        : filter.key === "mediaHandling"
          ? mediaOptions
          : filter.key === "player"
            ? playerOptions
            : numericValueOptions;
    const selectedValue = String(filter.value);
    const hasSelected = valueOptions.some((opt) => opt.value === selectedValue);
    if (!hasSelected && valueOptions[0]) {
      filter.value = textKey ? valueOptions[0].value : Number(valueOptions[0].value);
    }
    fillSelect(valSel, valueOptions, String(filter.value));

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "ranker-filter-remove";
    removeBtn.setAttribute(
      "aria-label",
      `Remove ${rankerFilterKeyLabel(filter.key)} filter`,
    );
    removeBtn.textContent = "×";

    keySel.addEventListener("change", () => {
      const nextKey = keySel.value as RankerFilterKey;
      const wasText = isRankerTextFilterKey(filter.key);
      const nextText = isRankerTextFilterKey(nextKey);
      filter.key = nextKey;
      if (wasText !== nextText) {
        filter.op = nextText ? "eq" : "gte";
      } else if (nextText && (filter.op === "gte" || filter.op === "lte")) {
        filter.op = "eq";
      }
      filter.value = defaultRankerFilterValue(nextKey);
      renderRankerFilters();
      refreshRankerListView();
    });
    opSel.addEventListener("change", () => {
      filter.op = opSel.value as RankerFilterOp;
      refreshRankerListView();
    });
    valSel.addEventListener("change", () => {
      filter.value = textKey ? valSel.value : Number(valSel.value);
      refreshRankerListView();
    });
    removeBtn.addEventListener("click", () => {
      const at = rankerFilters.findIndex((f) => f.id === filter.id);
      if (at < 0) return;
      rankerFilters.splice(at, 1);
      if (at === 0) {
        rankerFilterJoins.shift();
      } else {
        rankerFilterJoins.splice(at - 1, 1);
      }
      renderRankerFilters();
      refreshRankerListView();
    });

    row.append(keySel, opSel, valSel, removeBtn);
    rankerFilterRowsEl.append(row);
  });
}

rankerFilterToggleEl?.addEventListener("click", (event) => {
  event.stopPropagation();
  const open = rankerFilterPopoverEl?.hidden ?? true;
  if (open && rankerFilters.length === 0) {
    rankerFilters.push(newRankerFilter());
    renderRankerFilters();
    refreshRankerListView();
  } else {
    renderRankerFilters();
  }
  setRankerFilterPopoverOpen(open);
});

rankerFilterAddEl?.addEventListener("click", (event) => {
  event.stopPropagation();
  if (rankerFilters.length > 0) {
    rankerFilterJoins.push("and");
  }
  rankerFilters.push(newRankerFilter());
  renderRankerFilters();
  refreshRankerListView();
  setRankerFilterPopoverOpen(true);
});

rankerFilterPopoverEl?.addEventListener("click", (event) => {
  event.stopPropagation();
});

document.addEventListener("click", () => {
  if (rankerFilterPopoverEl && !rankerFilterPopoverEl.hidden) {
    setRankerFilterPopoverOpen(false);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && rankerFilterPopoverEl && !rankerFilterPopoverEl.hidden) {
    setRankerFilterPopoverOpen(false);
  }
});

function wireRankerSortHeader(
  th: HTMLElement,
  key: RankerSortKey,
  label: string,
  tip: string,
) {
  th.tabIndex = 0;
  th.role = "button";
  th.classList.add("ranker-th-sort");
  th.dataset.tip = tip;
  const sorted = key === "has" ? rankerSortKey === "has" : isRankerAttrSorted(key);
  const isAttrHighlight = key !== "has" && isRankerAttrSorted(key);
  th.classList.toggle("is-sorted", isAttrHighlight);
  th.setAttribute(
    "aria-sort",
    sorted ? (rankerSortAsc ? "ascending" : "descending") : "none",
  );
  const dirHint =
    rankerSortKey === key
      ? rankerSortAsc
        ? "ascending"
        : "descending"
      : "unsorted";
  th.setAttribute(
    "aria-label",
    `${label}: ${tip}. Sort ${dirHint}. Click to cycle sort.`,
  );

  th.addEventListener("mouseenter", () => showMetricTip(th, tip));
  th.addEventListener("mouseleave", hideMetricTip);
  th.addEventListener("focus", () => showMetricTip(th, tip));
  th.addEventListener("blur", hideMetricTip);

  const activate = (event: Event) => {
    event.preventDefault();
    hideMetricTip();
    cycleRankerSort(key);
    applyRankerSort();
  };
  th.addEventListener("click", activate);
  th.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      activate(event);
    }
  });
}

/** Attribute cells: keep integers compact so band ranges fit mid-density columns. */
function formatAttrNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function formatMidCell(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return formatAttrNumber(value);
}

/**
 * Squad tip mid: reserve 10s / 1s / .1s slots under tabular nums
 * (e.g. " 9  ", "14  ", " 9.5", "17.5") so places line up.
 */
function formatSquadTipMid(value: number): string {
  const text = formatAttrNumber(value);
  if (text.includes(".")) {
    const [whole = "", frac = ""] = text.split(".");
    return `${whole.padStart(2, " ")}.${frac}`;
  }
  return `${text.padStart(2, " ")}  `;
}

/** Pad 1–9 for `.fmt-band` cells (tabular nums + `white-space: pre`). */
function formatBandPart(value: number): string {
  const text = formatAttrNumber(value);
  return text.length < 2 ? text.padStart(2, " ") : text;
}

/** Table-ready band text for `.fmt-band` / `.attr-band` cells. */
function formatBandCell(band: { min: number; max: number } | null): string {
  if (!band) return "—";
  return `${formatBandPart(band.min)} - ${formatBandPart(band.max)}`;
}


function createAttrCell(
  entry: ComboRankEntry,
  col: RankAttrCol,
): HTMLTableCellElement {
  const td = document.createElement("td");
  td.className = attrColClass(col, rankerValueMode);

  const mid = entry.mids[col.key];
  const band = entry.bands[col.key];
  const midText = formatMidCell(mid);
  const bandText = formatBandCell(band);
  // Cache both modes so Mid↔Band can flip without re-ranking / rebuild.
  td.dataset.midText = midText;
  td.dataset.bandText = bandText;
  const text = rankerValueMode === "band" ? bandText : midText;
  td.textContent = text;

  if (text === "—") {
    td.classList.add("is-empty");
    return td;
  }

  if (col.toneAttr && mid !== null) {
    const tone = attributeTone(col.toneAttr, mid);
    if (tone !== "neutral") td.classList.add(tone);
  }
  if (isRankerAttrSorted(col.key)) td.classList.add("is-sorted-col");
  return td;
}

/** Instant Mid↔Band swap — updates text only, no rank/DOM rebuild. */
function applyRankerValueMode() {
  // Band vs mid changes filter semantics — rebuild when filters are active.
  if (rankerFilters.length > 0) {
    refreshRankerListView();
    return;
  }
  const wantBand = rankerValueMode === "band";
  const cells =
    rankerListEl.querySelectorAll<HTMLTableCellElement>("td.ranker-col-mid");
  for (const cell of cells) {
    const text = wantBand
      ? (cell.dataset.bandText ?? "—")
      : (cell.dataset.midText ?? "—");
    cell.classList.toggle("is-band", wantBand);
    cell.classList.toggle("is-empty", text === "—");
    if (cell.textContent !== text) cell.textContent = text;
  }
  // Density may change (bands are wider) — defer so the click paints first.
  scheduleRankerDensitySync();
}

function renderRankerPodium(entries: ComboRankEntry[]) {
  rankerPodiumEl.replaceChildren();
  const top = entries.slice(0, 3);
  if (top.length === 0) {
    const empty = document.createElement("p");
    empty.className = "ranker-empty";
    empty.textContent =
      rankerFilters.length > 0
        ? "No combos match the current filters."
        : "No compatible personality / media combos found.";
    rankerPodiumEl.append(empty);
    return;
  }

  // Visual order: 2nd · 1st · 3rd via CSS order on data-place (podium spot,
  // not global catalog rank — filters often surface #59+ as the local top 3).
  top.forEach((entry, index) => {
    const podiumPlace = index + 1;
    const slot = document.createElement("article");
    slot.className = "ranker-podium-slot is-probeable";
    slot.dataset.place = String(podiumPlace);
    if (podiumPlace === 1) slot.dataset.cardSize = "large";
    slot.tabIndex = 0;
    slot.role = "button";
    slot.setAttribute(
      "aria-label",
      `Probe ${entry.personality}, ${entry.mediaHandling}`,
    );

    const place = document.createElement("span");
    place.className = "ranker-place";
    if (entry.tone === "good") place.classList.add("is-good");
    if (entry.tone === "bad") place.classList.add("is-bad");
    place.textContent = `#${entry.rank}`;

    const name = document.createElement("p");
    name.className = "ranker-combo-name";
    name.textContent = entry.personality;

    const media = document.createElement("p");
    media.className = "ranker-combo-media";
    media.textContent = entry.mediaHandling;

    const meta = document.createElement("div");
    meta.className = "ranker-podium-meta";
    meta.append(createHaBadge(entry.haScore, entry.tone));

    slot.append(place, name, media, meta);
    setPodiumPopulationLabel(slot, entry.label);
    slot.title = rankerEntryTitle(entry);

    const openFromPodium = (event: Event) => {
      event.preventDefault();
      applyCheckerCombo(entry, { navigate: true });
    };
    slot.addEventListener("click", openFromPodium);
    slot.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") openFromPodium(event);
    });

    if (podiumPlace === 1 && shouldShowProbeNudge()) {
      slot.classList.add("is-probe-nudge");
      slot.append(createProbeNudge());
    }

    rankerPodiumEl.append(slot);
  });
}

function renderRankerList(entries: ComboRankEntry[]) {
  rankerListEl.replaceChildren();
  if (entries.length === 0) return;

  const table = document.createElement("table");
  table.className = "ranker-list-table fmt-table";

  const colgroup = document.createElement("colgroup");
  const appendCol = (className: string) => {
    const col = document.createElement("col");
    col.className = className;
    colgroup.append(col);
  };
  appendCol("ranker-col-rank");
  appendCol("ranker-col-personality");
  appendCol("ranker-col-label");
  for (const col of RANK_ATTR_COLS) {
    appendCol(`ranker-col-mid ranker-attr-${col.showFrom}`);
  }
  appendCol("ranker-col-ha");
  table.append(colgroup);

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  const appendTh = (
    text: string,
    options?: { className?: string; tip?: string },
  ) => {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = text;
    if (options?.className) th.className = options.className;
    if (options?.tip) {
      th.dataset.tip = options.tip;
      th.tabIndex = 0;
      th.classList.add("ranker-th-tip");
      th.setAttribute("aria-label", `${text}: ${options.tip}`);
    }
    headRow.append(th);
    return th;
  };
  appendTh("#", { className: "ranker-col-rank" });
  appendTh("Personality", { className: "ranker-col-personality" });

  const typeTh = document.createElement("th");
  typeTh.scope = "col";
  typeTh.className = "ranker-col-label ranker-th-filter";
  typeTh.tabIndex = 0;
  typeTh.role = "button";
  typeTh.textContent = populationFilterLabel(rankerPopulation);
  typeTh.dataset.tip = "Click to cycle MIXED · REAL · NEWGEN";
  typeTh.setAttribute(
    "aria-label",
    `Type filter ${populationFilterLabel(rankerPopulation)}. Click to cycle MIXED, REAL, NEWGEN.`,
  );
  typeTh.addEventListener("mouseenter", () =>
    showMetricTip(typeTh, typeTh.dataset.tip ?? ""),
  );
  typeTh.addEventListener("mouseleave", hideMetricTip);
  typeTh.addEventListener("focus", () =>
    showMetricTip(typeTh, typeTh.dataset.tip ?? ""),
  );
  typeTh.addEventListener("blur", hideMetricTip);
  const cycleType = (event: Event) => {
    event.preventDefault();
    hideMetricTip();
    rankerPopulation = cycleRankerPopulation();
    renderPersonalityRanker();
  };
  typeTh.addEventListener("click", cycleType);
  typeTh.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      cycleType(event);
    }
  });
  headRow.append(typeTh);

  for (const col of RANK_ATTR_COLS) {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = col.header;
    th.className = `ranker-col-mid ranker-attr-${col.showFrom}`;
    wireRankerSortHeader(th, col.key, col.header, col.title);
    headRow.append(th);
  }
  {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = "HAS";
    th.className = "ranker-col-ha";
    wireRankerSortHeader(th, "has", "HAS", "Hidden Attribute Score");
    headRow.append(th);
  }
  thead.append(headRow);
  table.append(thead);

  const body = document.createElement("tbody");
  for (const entry of entries) {
    const row = document.createElement("tr");
    row.dataset.personality = entry.personality;
    row.dataset.media = entry.mediaHandling;
    if (entry.label) row.dataset.label = entry.label;
    row.title = rankerEntryTitle(entry);

    const rankCell = document.createElement("td");
    rankCell.className = "ranker-col-rank";
    if (entry.tone === "good") rankCell.classList.add("is-good");
    if (entry.tone === "bad") rankCell.classList.add("is-bad");
    rankCell.textContent = String(entry.rank);

    const comboCell = document.createElement("td");
    comboCell.className = "ranker-col-personality";
    comboCell.tabIndex = 0;
    comboCell.role = "button";
    comboCell.setAttribute(
      "aria-label",
      `Probe ${entry.personality}, ${entry.mediaHandling}`,
    );
    const combo = document.createElement("div");
    combo.className = "ranker-list-combo";
    const strong = document.createElement("strong");
    strong.textContent = entry.personality;
    const media = document.createElement("span");
    media.textContent = entry.mediaHandling;
    combo.append(strong, media);
    comboCell.append(combo);
    const openInChecker = (event: Event) => {
      event.preventDefault();
      event.stopPropagation();
      applyCheckerCombo(entry, { navigate: true });
    };
    comboCell.addEventListener("click", openInChecker);
    comboCell.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        openInChecker(event);
      }
    });

    const labelCell = document.createElement("td");
    labelCell.className = "ranker-col-label";
    labelCell.append(createPopulationLabel(entry.label));

    row.append(rankCell, comboCell, labelCell);

    for (const col of RANK_ATTR_COLS) {
      row.append(createAttrCell(entry, col));
    }

    const haCell = document.createElement("td");
    haCell.className = "ranker-col-ha";
    const haBadge = createHaBadge(entry.haScore, entry.tone);
    wireRankerHaAttrsTip(haBadge, row);
    haCell.append(haBadge);

    row.append(haCell);
    body.append(row);
  }
  table.append(body);
  rankerListEl.append(table);
}

function clearRankerHits() {
  for (const row of rankerListEl.querySelectorAll<HTMLTableRowElement>(
    "tr.is-ranker-hit",
  )) {
    row.classList.remove("is-ranker-hit");
  }
}

function rankerRowHaystack(row: HTMLTableRowElement): string {
  return normalizeKey(
    `${row.dataset.personality ?? ""} ${row.dataset.media ?? ""} ${row.dataset.label ?? ""}`,
  ).replace(/,/g, " ");
}

function rankerRowMatchesQuery(
  row: HTMLTableRowElement,
  tokens: string[],
): boolean {
  if (tokens.length === 0) return false;
  const haystack = rankerRowHaystack(row);
  return tokens.every((token) => haystack.includes(token));
}

function collectRankerMatches(query: string): HTMLTableRowElement[] {
  const tokens = rankerSearchTokens(query);
  if (tokens.length === 0) return [];
  return [
    ...rankerListEl.querySelectorAll<HTMLTableRowElement>("tbody tr"),
  ].filter((row) => rankerRowMatchesQuery(row, tokens));
}

function updateRankerFindChrome() {
  const total = rankerMatches.length;
  const hasQuery = Boolean(rankerSearchEl?.value.trim());
  if (!hasQuery) {
    rankerFindCountEl.textContent = "";
  } else if (total === 0) {
    rankerFindCountEl.textContent = "0 / 0";
  } else {
    rankerFindCountEl.textContent = `${rankerMatchIndex + 1} / ${total}`;
  }
  const enabled = total > 0;
  rankerFindPrevEl.disabled = !enabled;
  rankerFindNextEl.disabled = !enabled;
}

function scrollRankerMatchIntoView(row: HTMLTableRowElement) {
  const scroller = rankerListEl;
  const thead = scroller.querySelector("thead");
  const headerOffset = thead?.getBoundingClientRect().height ?? 0;

  const scrollerRect = scroller.getBoundingClientRect();
  const rowRect = row.getBoundingClientRect();
  // Visible band below the sticky header — aim the hit at its vertical center.
  const visibleTop = scrollerRect.top + headerOffset;
  const visibleHeight = Math.max(0, scrollerRect.bottom - visibleTop);
  const rowCenter = (rowRect.top + rowRect.bottom) / 2;
  const targetCenter = visibleTop + visibleHeight / 2;
  const delta = rowCenter - targetCenter;

  if (Math.abs(delta) < 2) return;
  scroller.scrollBy({ top: delta, behavior: "smooth" });
}

function showRankerMatch(index: number) {
  clearRankerHits();
  const total = rankerMatches.length;
  if (total === 0) {
    rankerMatchIndex = 0;
    updateRankerFindChrome();
    return;
  }
  rankerMatchIndex = ((index % total) + total) % total;
  const match = rankerMatches[rankerMatchIndex]!;
  match.classList.add("is-ranker-hit");
  scrollRankerMatchIntoView(match);
  updateRankerFindChrome();
}

/** Recompute matches and jump to the first (or keep position when refreshing). */
function refreshRankerFind(options?: { keepIndex?: boolean }) {
  const previous = rankerMatches[rankerMatchIndex];
  rankerMatches = collectRankerMatches(rankerSearchEl.value);
  if (rankerMatches.length === 0) {
    clearRankerHits();
    rankerMatchIndex = 0;
    updateRankerFindChrome();
    return;
  }
  if (options?.keepIndex && previous) {
    const still = rankerMatches.indexOf(previous);
    showRankerMatch(still >= 0 ? still : 0);
    return;
  }
  showRankerMatch(0);
}

function stepRankerFind(delta: number) {
  if (rankerMatches.length === 0) {
    refreshRankerFind();
    return;
  }
  showRankerMatch(rankerMatchIndex + delta);
}

function renderPersonalityRanker() {
  if (!rankerPodiumEl || !rankerListEl) return;
  const ranking = rankPersonalityMediaCombosUnified(catalog, {
    population: rankerPopulation,
  });
  lastRankerEntries = ranking.entries;
  catalogEliteHasFloor = ranking.eliteHasFloor;
  catalogPoorHasCeiling = ranking.poorHasCeiling;
  refreshRankerListView();
}

/**
 * Density tiers (fit-based, no viewport breakpoints):
 * narrow → # Personality Type HAS
 * mid    → + Pro Pre Amb Tem Loy Spo Con (weight order)
 * wide   → + Det / Lea in their weighted slots (Det before Pro, Lea after Tem)
 */
function measureRankerProbeWidth(
  table: HTMLTableElement,
  density: "mid" | "wide",
): number {
  // Sample only header + a few rows — column intrinsic width is the same.
  const probe = document.createElement("table");
  probe.setAttribute("aria-hidden", "true");
  probe.className = "ranker-list-table fmt-table";
  probe.style.cssText =
    "position:absolute;left:-100000px;top:0;visibility:hidden;pointer-events:none;width:max-content;table-layout:auto;";

  const colgroup = table.querySelector("colgroup");
  const thead = table.querySelector("thead");
  if (colgroup) probe.append(colgroup.cloneNode(true));
  if (thead) probe.append(thead.cloneNode(true));

  const body = document.createElement("tbody");
  const sourceRows = table.querySelectorAll("tbody tr");
  const sample = Math.min(3, sourceRows.length);
  for (let i = 0; i < sample; i += 1) {
    body.append(sourceRows[i]!.cloneNode(true));
  }
  probe.append(body);

  const showWide = density === "wide";
  for (const cell of probe.querySelectorAll<HTMLElement>(".ranker-col-mid")) {
    const isWideOnly = cell.classList.contains("ranker-attr-wide");
    const show = showWide || !isWideOnly;
    cell.style.display = show ? "table-cell" : "none";
    cell.style.visibility = show ? "visible" : "collapse";
    cell.style.width = "auto";
    cell.style.minWidth = "0";
  }
  for (const col of probe.querySelectorAll<HTMLElement>("col.ranker-col-mid")) {
    const isWideOnly = col.classList.contains("ranker-attr-wide");
    const show = showWide || !isWideOnly;
    col.style.visibility = show ? "visible" : "collapse";
    col.style.width = show ? "auto" : "0";
  }

  document.body.append(probe);
  const width = probe.scrollWidth;
  probe.remove();
  return width;
}

function pickRankerDensity(
  available: number,
  needMid: number,
  needWide: number,
  current: RankerDensity,
): RankerDensity {
  // Hysteresis so resizing / Mid↔Band doesn't thrash tiers.
  const enterWide = needWide <= available - 24;
  const leaveWide = needWide > available + 8;
  const enterMid = needMid <= available - 24;
  const leaveMid = needMid > available + 8;

  if (current === "wide") {
    if (!leaveWide) return "wide";
    return leaveMid ? "narrow" : "mid";
  }
  if (current === "mid") {
    if (enterWide) return "wide";
    if (!leaveMid) return "mid";
    return "narrow";
  }
  // narrow
  if (enterWide) return "wide";
  if (enterMid) return "mid";
  return "narrow";
}

function syncRankerDensity() {
  if (rankEl.hidden) return;
  const table = rankerListEl.querySelector<HTMLTableElement>("table");
  if (!table) return;

  const available = rankerListEl.clientWidth;
  if (available <= 0) return;

  const needMid = measureRankerProbeWidth(table, "mid");
  const needWide = measureRankerProbeWidth(table, "wide");
  const current = parseRankerDensity(rankEl.dataset.density);
  const next = pickRankerDensity(available, needMid, needWide, current);
  if (rankEl.dataset.density !== next) {
    rankEl.dataset.density = next;
  }
}

let rankerDensityRaf = 0;
function scheduleRankerDensitySync() {
  window.cancelAnimationFrame(rankerDensityRaf);
  rankerDensityRaf = window.requestAnimationFrame(() => {
    rankerDensityRaf = window.requestAnimationFrame(() => {
      syncRankerDensity();
    });
  });
}

const rankerDensityObserver = new ResizeObserver(() => {
  scheduleRankerDensitySync();
});
rankerDensityObserver.observe(rankerListEl);

function syncRankerModeButtons() {
  for (const btn of document.querySelectorAll<HTMLButtonElement>(
    "[data-ranker-values]",
  )) {
    const mode = btn.dataset.rankerValues;
    btn.setAttribute("aria-pressed", String(mode === rankerValueMode));
  }
}

for (const btn of document.querySelectorAll<HTMLButtonElement>(
  "[data-ranker-values]",
)) {
  btn.addEventListener("click", () => {
    const next = btn.dataset.rankerValues;
    if (next !== "mid" && next !== "band") return;
    if (next === rankerValueMode) return;
    rankerValueMode = next;
    syncRankerModeButtons();
    applyRankerValueMode();
  });
}

rankerSearchEl?.addEventListener("input", () => {
  refreshRankerFind();
});

rankerSearchEl?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    stepRankerFind(event.shiftKey ? -1 : 1);
    return;
  }
  if (event.key === "F3") {
    event.preventDefault();
    stepRankerFind(event.shiftKey ? -1 : 1);
  }
});

rankerFindPrevEl?.addEventListener("click", () => {
  stepRankerFind(-1);
});

rankerFindNextEl?.addEventListener("click", () => {
  stepRankerFind(1);
});

rankerListEl.addEventListener("scroll", hideMetricTip, { passive: true });

function formatClimbDelta(delta: number | undefined): string {
  if (delta === undefined || !Number.isFinite(delta) || Math.abs(delta) < 0.05) {
    return "—";
  }
  const rounded = Math.round(delta * 10) / 10;
  const text = Number.isInteger(rounded)
    ? String(rounded)
    : rounded.toFixed(1);
  return rounded > 0 ? `+${text}` : text;
}

/**
 * Compare Δ keeps the raw numeric sign (3 vs 7.5 → −4.5), but `is-up` /
 * `is-down` mean better / worse for that attribute. Controversy is inverted.
 */
function compareAttrDeltaQualityClass(
  attribute: (typeof CHECKER_TABLE_ATTRIBUTES)[number],
  delta: number,
): "is-up" | "is-down" | "" {
  const betterIsHigher = attribute !== "controversy";
  const improved = betterIsHigher ? delta > 0 : delta < 0;
  const worsened = betterIsHigher ? delta < 0 : delta > 0;
  if (improved) return "is-up";
  if (worsened) return "is-down";
  return "";
}

function formatBandSpan(band: { min: number; max: number } | undefined): string {
  // Same padded band rendering as Rank HAS cells (aligns 1–9 with 10–20).
  return formatBandCell(band ?? null);
}

function renderEmptyAttributeRows() {
  attrBodyEl.replaceChildren();
  attrTableEl.removeAttribute("title");
  renderHaScore(null);
  for (const attribute of MODELED_HAS_ATTRIBUTES) {
    const row = document.createElement("tr");
    row.classList.add("is-empty");
    row.dataset.attribute = attribute;
    row.innerHTML = `
      <td>
        <span class="attr-name" title="${ATTRIBUTE_DESCRIPTIONS[attribute]}">
          ${ATTRIBUTE_LABELS[attribute]}
        </span>
      </td>
      <td class="attr-band fmt-band is-empty">—</td>
      <td class="attr-mid fmt-mid is-empty">—</td>
    `;
    row.dataset.playerTone = "neutral";
    attrBodyEl.append(row);
  }
}

function clearResults() {
  renderEmptyAttributeRows();
  statusEl.hidden = true;
  statusEl.textContent = "";
  lastImpliedVisible = {};
  syncQuickPicks();
}

function snapshotFrom(result: EstimateResult): PlayerEntry["snapshot"] {
  const snapshot: PlayerEntry["snapshot"] = {};
  for (const attribute of HAS_ATTRIBUTES) {
    if (isUnmodeledHiddenAttribute(attribute)) continue;
    const estimate = result.attributes[attribute];
    snapshot[attribute] = {
      min: estimate.min,
      max: estimate.max,
      midpoint: estimate.midpoint,
    };
  }
  return snapshot;
}

function fillLabelSelects() {
  labelGameVersionEl.replaceChildren();
  const blankGame = document.createElement("option");
  blankGame.value = "";
  blankGame.textContent = "—";
  labelGameVersionEl.append(blankGame);
  for (const version of FM_GAME_VERSIONS) {
    const option = document.createElement("option");
    option.value = version;
    option.textContent = version;
    labelGameVersionEl.append(option);
  }

  labelDatabaseEl.replaceChildren();
  const blankDb = document.createElement("option");
  blankDb.value = "";
  blankDb.textContent = "—";
  labelDatabaseEl.append(blankDb);
  for (const version of FM_DATABASE_VERSIONS) {
    const option = document.createElement("option");
    option.value = version;
    option.textContent = version;
    labelDatabaseEl.append(option);
  }
  const custom = document.createElement("option");
  custom.value = CUSTOM_DATABASE_VALUE;
  custom.textContent = "Custom…";
  labelDatabaseEl.append(custom);
}

function syncCustomDatabaseVisibility() {
  const custom = labelDatabaseEl.value === CUSTOM_DATABASE_VALUE;
  labelDatabaseEl.hidden = custom;
  labelDatabaseCustomWrapEl.hidden = !custom;
}

function setFormEnabled(form: HTMLFormElement, enabled: boolean) {
  for (const el of Array.from(form.elements)) {
    if (
      el instanceof HTMLInputElement ||
      el instanceof HTMLSelectElement ||
      el instanceof HTMLButtonElement ||
      el instanceof HTMLTextAreaElement
    ) {
      el.disabled = !enabled;
    }
  }
}

function setLabelFormEnabled() {
  const saveEnabled =
    history.panel === "saves" && Boolean(findSave(history, history.activeSaveId));
  const playerEnabled =
    history.panel === "players" &&
    Boolean(
      findPlayer(history, history.activeSaveId, history.activePlayerId),
    );
  setFormEnabled(saveFormEl, saveEnabled);
  setFormEnabled(playerLabelFormEl, playerEnabled);
}

function playerEditHeading(player: PlayerEntry): string {
  const name = player.labels.playerName?.trim();
  return name || formatStamp(player.createdAt);
}

function setLabelHeading(text: string) {
  labelHeadingEl.textContent = text;
  labelHeadingEl.title = text;
}

function fillSaveForm(save: GameSave | null) {
  suppressLabelSync = true;
  try {
    if (!save) {
      if (history.panel === "saves") {
        setLabelHeading("Select a save.");
      }
      labelGameVersionEl.value = "";
      labelDatabaseEl.value = "";
      labelDatabaseCustomEl.value = "";
      labelGameSaveEl.value = "";
      syncCustomDatabaseVisibility();
      setLabelFormEnabled();
      return;
    }

    if (history.panel === "saves") {
      setLabelHeading(save.name.trim() || formatStamp(save.createdAt));
    }
    labelGameVersionEl.value = save.gameVersion ?? "";

    const db = save.database ?? "";
    if (db && !(FM_DATABASE_VERSIONS as readonly string[]).includes(db)) {
      labelDatabaseEl.value = CUSTOM_DATABASE_VALUE;
      labelDatabaseCustomEl.value = db;
    } else {
      labelDatabaseEl.value = db;
      labelDatabaseCustomEl.value = "";
    }
    syncCustomDatabaseVisibility();

    labelGameSaveEl.value = save.name;
    setLabelFormEnabled();
  } finally {
    suppressLabelSync = false;
  }
}

function fillPlayerForm(player: PlayerEntry | null) {
  suppressLabelSync = true;
  try {
    if (!player) {
      if (history.panel === "players") {
        setLabelHeading("Select a player.");
      }
      labelPlayerIdEl.value = "";
      labelPlayerNameEl.value = "";
      labelPlayerPositionEl.value = "";
      setLabelFormEnabled();
      return;
    }
    setLabelHeading(playerEditHeading(player));
    labelPlayerIdEl.value = player.labels.playerId ?? "";
    labelPlayerNameEl.value = player.labels.playerName ?? "";
    labelPlayerPositionEl.value = player.labels.position ?? "";
    setLabelFormEnabled();
  } finally {
    suppressLabelSync = false;
  }
}

function readSaveForm(): Pick<GameSave, "name" | "gameVersion" | "database"> {
  const value: Pick<GameSave, "name" | "gameVersion" | "database"> = {
    name: labelGameSaveEl.value.trim(),
  };
  if (labelGameVersionEl.value) value.gameVersion = labelGameVersionEl.value;
  if (labelDatabaseEl.value === CUSTOM_DATABASE_VALUE) {
    const custom = labelDatabaseCustomEl.value.trim();
    if (custom) value.database = custom;
  } else if (labelDatabaseEl.value) {
    value.database = labelDatabaseEl.value;
  }
  return value;
}

function readPlayerLabels(): PlayerLabels {
  const labels: PlayerLabels = {};
  if (labelPlayerIdEl.value.trim()) {
    labels.playerId = labelPlayerIdEl.value.trim();
  }
  if (labelPlayerNameEl.value.trim()) {
    labels.playerName = labelPlayerNameEl.value.trim();
  }
  if (labelPlayerPositionEl.value.trim()) {
    labels.position = labelPlayerPositionEl.value.trim();
  }
  return labels;
}

function orderedItems<T extends { editedAt?: string; createdAt: string }>(
  items: T[],
): T[] {
  return [...items].sort((a, b) => {
    const byActivity = sortKey(b).localeCompare(sortKey(a));
    if (byActivity !== 0) return byActivity;
    return b.createdAt.localeCompare(a.createdAt);
  });
}

type PlayerSortKey =
  | "createdAt"
  | "updatedAt"
  | "ha"
  | "determination"
  | "leadership"
  | "professionalism"
  | "ambition"
  | "pressure"
  | "temperament"
  | "loyalty"
  | "sportsmanship"
  | "controversy";

let playerSortKey: PlayerSortKey = "updatedAt";
let playerSortAsc = false;

function playerSortValue(player: PlayerEntry, key: PlayerSortKey): string | number {
  if (key === "createdAt") return player.createdAt;
  if (key === "updatedAt") return player.updatedAt;
  if (key === "ha") return haScoreFromSnapshot(player.snapshot) ?? Number.NEGATIVE_INFINITY;
  if (key === "determination") {
    return player.signals.determination ?? Number.NEGATIVE_INFINITY;
  }
  if (key === "leadership") {
    return player.signals.leadership ?? Number.NEGATIVE_INFINITY;
  }
  return player.snapshot[key]?.midpoint ?? Number.NEGATIVE_INFINITY;
}

function orderedPlayers(players: PlayerEntry[]): PlayerEntry[] {
  const dir = playerSortAsc ? 1 : -1;
  return [...players].sort((a, b) => {
    const av = playerSortValue(a, playerSortKey);
    const bv = playerSortValue(b, playerSortKey);
    if (typeof av === "string" && typeof bv === "string") {
      const cmp = av.localeCompare(bv);
      if (cmp !== 0) return cmp * dir;
    } else {
      const an = typeof av === "number" ? av : Number.NEGATIVE_INFINITY;
      const bn = typeof bv === "number" ? bv : Number.NEGATIVE_INFINITY;
      if (an !== bn) return (an < bn ? -1 : 1) * dir;
    }
    return a.createdAt.localeCompare(b.createdAt) * dir;
  });
}

function syncPlayerSortControls() {
  historySortByEl.value = playerSortKey;
  historySortDirEl.dataset.dir = playerSortAsc ? "asc" : "desc";
  historySortDirEl.textContent = playerSortAsc ? "A→Z" : "Z→A";
  historySortDirEl.title = playerSortAsc
    ? "A→Z (low → high)"
    : "Z→A (high → low)";
  historySortDirEl.setAttribute(
    "aria-label",
    playerSortAsc ? "Sort ascending" : "Sort descending",
  );
}

const COMPARE_MIN_SLOTS = 2;
const COMPARE_MAX_SLOTS = 3;
const COMPARE_DRAFT_KEY = "fmt.compareDraft";

type CompareSlotState = {
  id: string;
  label: string;
  personality: string;
  mediaHandling: string;
  determination: string;
  leadership: string;
  age: string;
  isRegen: boolean;
  sourceSaveId?: string;
  sourcePlayerId?: string;
};

type CompareSlotResult = {
  slotId: string;
  result: EstimateResult | null;
  error?: string;
  rank?: number;
  score?: number;
  tone: "good" | "bad" | "neutral";
};

let compareSlots: CompareSlotState[] = [];
let compareResults: CompareSlotResult[] = [];
type CompareViewMode = "table" | "graph";
type ComparePlotMode = "mid" | "band" | "min" | "max";
let compareViewMode: CompareViewMode = "table";
let comparePlotMode: ComparePlotMode = "mid";

function isComparePlotMode(value: string): value is ComparePlotMode {
  return (
    value === "mid" || value === "band" || value === "min" || value === "max"
  );
}

/** Attributes probe order: known visibles interleaved by weight, Imp omitted. */
const COMPARE_RADAR_ATTRS = CHECKER_TABLE_ATTRIBUTES;

const COMPARE_RADAR_COLORS = [
  { stroke: "#3ecf8e", fill: "rgba(62, 207, 142, 0.22)" },
  { stroke: "#5b9cff", fill: "rgba(91, 156, 255, 0.2)" },
  { stroke: "#e6b84d", fill: "rgba(230, 184, 77, 0.2)" },
] as const;

function newCompareSlotId(): string {
  return `cmp-${crypto.randomUUID()}`;
}

function emptyCompareSlot(): CompareSlotState {
  return {
    id: newCompareSlotId(),
    label: "",
    personality: "",
    mediaHandling: "",
    determination: "",
    leadership: "",
    age: "",
    isRegen: true,
  };
}

function defaultCompareSlots(): CompareSlotState[] {
  return [emptyCompareSlot(), emptyCompareSlot()];
}

function readCompareDraft(): CompareSlotState[] | null {
  try {
    const raw = window.localStorage.getItem(COMPARE_DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { slots?: Partial<CompareSlotState>[] };
    if (!parsed?.slots || !Array.isArray(parsed.slots)) return null;
    const slots = parsed.slots
      .slice(0, COMPARE_MAX_SLOTS)
      .map((slot, index) => {
        return {
          id:
            typeof slot.id === "string" && slot.id
              ? slot.id
              : newCompareSlotId(),
          label: typeof slot.label === "string" ? slot.label : `Player ${index + 1}`,
          personality:
            typeof slot.personality === "string" ? slot.personality : "",
          mediaHandling:
            typeof slot.mediaHandling === "string" ? slot.mediaHandling : "",
          determination:
            typeof slot.determination === "string" ? slot.determination : "",
          leadership:
            typeof slot.leadership === "string" ? slot.leadership : "",
          age: typeof slot.age === "string" ? slot.age : "",
          isRegen: slot.isRegen !== false,
          ...(typeof slot.sourceSaveId === "string"
            ? { sourceSaveId: slot.sourceSaveId }
            : {}),
          ...(typeof slot.sourcePlayerId === "string"
            ? { sourcePlayerId: slot.sourcePlayerId }
            : {}),
        } satisfies CompareSlotState;
      });
    while (slots.length < COMPARE_MIN_SLOTS) slots.push(emptyCompareSlot());
    return slots;
  } catch {
    return null;
  }
}

function persistCompareDraft() {
  try {
    window.localStorage.setItem(
      COMPARE_DRAFT_KEY,
      JSON.stringify({ slots: compareSlots }),
    );
  } catch {
    // ignore private-mode / quota failures
  }
}

function ensureCompareSlots() {
  if (compareSlots.length >= COMPARE_MIN_SLOTS) return;
  compareSlots = readCompareDraft() ?? defaultCompareSlots();
}

function slotDisplayName(slot: CompareSlotState, index: number): string {
  const label = slot.label.trim();
  if (label) return label;
  if (slot.personality.trim()) return slot.personality.trim();
  return `Player ${index + 1}`;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

type SquadNameOption = {
  kind: "existing" | "create";
  value: string;
  label: string;
  name: string;
  saveId?: string;
  playerId?: string;
};

function playerDisplayName(player: PlayerEntry): string {
  return (
    player.labels.playerName?.trim() ||
    player.title?.trim() ||
    player.signals.personality ||
    "Unnamed"
  );
}

function squadNameOptions(query: string): SquadNameOption[] {
  const key = query.trim().toLowerCase();
  const options: SquadNameOption[] = [];
  let exactName = false;
  for (const save of history.saves) {
    for (const player of save.players) {
      const name = playerDisplayName(player);
      const label = `${save.name || "Untitled"} · ${name}`;
      if (name.toLowerCase() === key) exactName = true;
      if (
        key &&
        !name.toLowerCase().includes(key) &&
        !save.name.toLowerCase().includes(key) &&
        !label.toLowerCase().includes(key)
      ) {
        continue;
      }
      options.push({
        kind: "existing",
        value: `${save.id}:${player.id}`,
        label,
        name,
        saveId: save.id,
        playerId: player.id,
      });
    }
  }
  options.sort((a, b) => a.label.localeCompare(b.label));
  const createName = query.trim();
  if (createName && !exactName) {
    options.unshift({
      kind: "create",
      value: `__create__:${createName}`,
      label: `Create “${createName}”`,
      name: createName,
    });
  }
  return options;
}

function findCompareSlot(id: string): CompareSlotState | undefined {
  return compareSlots.find((slot) => slot.id === id);
}

function slotIsLinked(slot: CompareSlotState): boolean {
  return Boolean(slot.sourceSaveId && slot.sourcePlayerId);
}

function signalsFromCompareSlot(slot: CompareSlotState): HistorySignals {
  const determination = safeOptionalInt(slot.determination);
  const leadership = safeOptionalInt(slot.leadership);
  const age = safeOptionalInt(slot.age);
  return {
    personality: slot.personality.trim(),
    mediaHandling: slot.mediaHandling.trim(),
    isRegen: slot.isRegen,
    ...(determination !== undefined ? { determination } : {}),
    ...(leadership !== undefined ? { leadership } : {}),
    ...(age !== undefined ? { age } : {}),
  };
}

function ensureCompareTargetSave(): GameSave {
  let save = findSave(history, history.activeSaveId);
  if (!save) {
    save = blankSave();
    history.saves.unshift(save);
    history.activeSaveId = save.id;
  }
  return save;
}

function applySquadPlayerToSlot(
  slot: CompareSlotState,
  saveId: string,
  playerId: string,
) {
  const player = findPlayer(history, saveId, playerId);
  if (!player) return;
  const signals = player.signals;
  slot.sourceSaveId = saveId;
  slot.sourcePlayerId = playerId;
  slot.label = playerDisplayName(player);
  slot.personality = signals.personality ?? "";
  slot.mediaHandling = signals.mediaHandling ?? "";
  slot.determination =
    signals.determination !== undefined ? String(signals.determination) : "";
  slot.leadership =
    signals.leadership !== undefined ? String(signals.leadership) : "";
  slot.age = signals.age !== undefined ? String(signals.age) : "";
  slot.isRegen = Boolean(signals.isRegen);
}

function createComparePlayer(slot: CompareSlotState, name: string) {
  const trimmed = name.trim();
  if (!trimmed) return;
  const save = ensureCompareTargetSave();
  const existing = save.players.find(
    (player) => playerDisplayName(player).toLowerCase() === trimmed.toLowerCase(),
  );
  if (existing) {
    applySquadPlayerToSlot(slot, save.id, existing.id);
    return;
  }
  const entry = blankPlayer(signalsFromCompareSlot(slot));
  entry.labels = { ...entry.labels, playerName: trimmed };
  entry.title = trimmed;
  save.players.unshift(entry);
  save.updatedAt = entry.updatedAt;
  slot.sourceSaveId = save.id;
  slot.sourcePlayerId = entry.id;
  slot.label = trimmed;
  schedulePersist();
  renderHistory();
}

function clearCompareSlotPlayer(slot: CompareSlotState) {
  const id = slot.id;
  Object.assign(slot, emptyCompareSlot());
  slot.id = id;
}

function syncLinkedComparePlayer(slot: CompareSlotState) {
  if (!slot.sourceSaveId || !slot.sourcePlayerId) return;
  const player = findPlayer(history, slot.sourceSaveId, slot.sourcePlayerId);
  if (!player) return;
  const now = new Date().toISOString();
  const name = slot.label.trim() || playerDisplayName(player);
  player.labels = { ...player.labels, playerName: name };
  player.signals = signalsFromCompareSlot(slot);
  player.title = name;
  player.updatedAt = now;
  const save = findSave(history, slot.sourceSaveId);
  if (save) save.updatedAt = now;
  schedulePersist();
}

function syncCompareSlotFromDom(slotEl: HTMLElement) {
  const slotId = slotEl.dataset.slotId;
  const slot = slotId ? findCompareSlot(slotId) : undefined;
  if (!slot) return;
  const label = slotEl.querySelector<HTMLInputElement>('input[data-field="label"]');
  const personality = slotEl.querySelector<HTMLInputElement>(
    'input[data-field="personality"]',
  );
  const media = slotEl.querySelector<HTMLInputElement>(
    'input[data-field="mediaHandling"]',
  );
  const determination = slotEl.querySelector<HTMLInputElement>(
    'input[data-field="determination"]',
  );
  const leadership = slotEl.querySelector<HTMLInputElement>(
    'input[data-field="leadership"]',
  );
  const age = slotEl.querySelector<HTMLInputElement>('input[data-field="age"]');
  const regen = slotEl.querySelector<HTMLInputElement>('input[data-field="isRegen"]');
  if (label && !slotIsLinked(slot)) slot.label = label.value;
  if (personality) slot.personality = personality.value;
  if (media) slot.mediaHandling = media.value;
  if (determination) slot.determination = determination.value;
  if (leadership) slot.leadership = leadership.value;
  if (age) slot.age = age.value;
  if (regen) slot.isRegen = regen.checked;
}

function selectedComparePersonality(
  slotEl: HTMLElement,
): PersonalityDefinition | undefined {
  const input = slotEl.querySelector<HTMLInputElement>(
    'input[data-field="personality"]',
  );
  const raw = input?.value.trim() ?? "";
  if (!raw) return undefined;
  return findPersonality(catalog, raw);
}

function selectedCompareMedia(
  slotEl: HTMLElement,
): MediaHandlingDefinition | undefined {
  const input = slotEl.querySelector<HTMLInputElement>(
    'input[data-field="mediaHandling"]',
  );
  const raw = input?.value.trim() ?? "";
  if (!raw) return undefined;
  try {
    return findMediaHandling(catalog, parseMediaHandlingInput(raw));
  } catch {
    return undefined;
  }
}

function bindCompareSquadNameCombo(
  slot: CompareSlotState,
  input: HTMLInputElement,
  listEl: HTMLUListElement,
) {
  let activeIndex = -1;
  let current: SquadNameOption[] = [];

  const close = () => {
    listEl.hidden = true;
    activeIndex = -1;
    input.setAttribute("aria-expanded", "false");
  };

  const commitOption = (opt: SquadNameOption) => {
    if (opt.kind === "existing" && opt.saveId && opt.playerId) {
      applySquadPlayerToSlot(slot, opt.saveId, opt.playerId);
    } else {
      createComparePlayer(slot, opt.name);
    }
    close();
    renderCompareSlots();
    runCompareEstimates();
  };

  const paint = () => {
    listEl.replaceChildren();
    if (current.length === 0) {
      listEl.hidden = true;
      input.setAttribute("aria-expanded", "false");
      return;
    }
    current.forEach((opt, index) => {
      const li = document.createElement("li");
      li.id = `${listEl.id}-opt-${index}`;
      li.setAttribute("role", "option");
      if (index === activeIndex) li.dataset.active = "true";
      const button = document.createElement("button");
      button.type = "button";
      if (index === activeIndex) button.setAttribute("aria-selected", "true");
      const label = document.createElement("span");
      label.className = "combo-option-label";
      label.textContent = opt.label;
      button.append(label);
      button.addEventListener("mousedown", (event) => {
        event.preventDefault();
        commitOption(opt);
      });
      li.append(button);
      listEl.append(li);
    });
    listEl.hidden = false;
    input.setAttribute("aria-expanded", "true");
  };

  const refresh = () => {
    current = squadNameOptions(input.value);
    activeIndex = current.length > 0 ? 0 : -1;
    paint();
  };

  input.addEventListener("focus", () => refresh());
  input.addEventListener("input", () => {
    slot.label = input.value;
    refresh();
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      close();
      return;
    }
    if (listEl.hidden || current.length === 0) {
      if (event.key === "Enter") {
        event.preventDefault();
        const name = input.value.trim();
        if (!name) return;
        createComparePlayer(slot, name);
        renderCompareSlots();
        runCompareEstimates();
      }
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      activeIndex = Math.min(current.length - 1, activeIndex + 1);
      paint();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      activeIndex = Math.max(0, activeIndex - 1);
      paint();
    } else if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      const opt = current[activeIndex];
      if (opt) commitOption(opt);
    }
  });
  input.addEventListener("blur", () => {
    window.setTimeout(close, 120);
  });
}

function bindCompareSlotCombos(slot: CompareSlotState, article: HTMLElement) {
  const personalityInput = article.querySelector<HTMLInputElement>(
    'input[data-field="personality"]',
  )!;
  const personalityList = article.querySelector<HTMLUListElement>(
    `ul[data-list="personality"]`,
  )!;
  const mediaInput = article.querySelector<HTMLInputElement>(
    'input[data-field="mediaHandling"]',
  )!;
  const mediaList = article.querySelector<HTMLUListElement>(
    `ul[data-list="media"]`,
  )!;
  const ageInput = article.querySelector<HTMLInputElement>(
    'input[data-field="age"]',
  )!;
  const detInput = article.querySelector<HTMLInputElement>(
    'input[data-field="determination"]',
  )!;
  const leadInput = article.querySelector<HTMLInputElement>(
    'input[data-field="leadership"]',
  )!;
  const regenInput = article.querySelector<HTMLInputElement>(
    'input[data-field="isRegen"]',
  )!;
  const regenChip = article.querySelector<HTMLButtonElement>(
    'button[data-field="isRegen-chip"]',
  )!;

  const commit = () => {
    syncCompareSlotFromDom(article);
    if (slotIsLinked(slot)) syncLinkedComparePlayer(slot);
    runCompareEstimates();
  };

  bindRegenChip(regenInput, regenChip, commit);

  const fields: PersonalityFieldSet = {
    ageEl: ageInput,
    isRegenEl: regenInput,
    determinationEl: detInput,
    leadershipEl: leadInput,
  };

  bindCombo(
    personalityInput,
    personalityList,
    () =>
      personalityComboOptions(
        regenInput.checked,
        safeOptionalInt(ageInput.value),
        selectedCompareMedia(article),
        safeOptionalInt(detInput.value),
        safeOptionalInt(leadInput.value),
      ),
    {
      onCommit: commit,
      isPersonality: true,
      siblingInput: mediaInput,
      siblingList: mediaList,
      getIsRegen: () => regenInput.checked,
      getAge: () => safeOptionalInt(ageInput.value),
      getSelectedMedia: () => selectedCompareMedia(article),
      getSelectedPersonality: () => selectedComparePersonality(article),
      getDetermination: () => safeOptionalInt(detInput.value),
      getLeadership: () => safeOptionalInt(leadInput.value),
      personalityFields: fields,
    },
  );

  bindCombo(
    mediaInput,
    mediaList,
    () => mediaComboOptions(selectedComparePersonality(article)),
    {
      onCommit: commit,
      isPersonality: false,
      siblingInput: personalityInput,
      siblingList: personalityList,
      getIsRegen: () => regenInput.checked,
      getAge: () => safeOptionalInt(ageInput.value),
      getSelectedMedia: () => selectedCompareMedia(article),
      getSelectedPersonality: () => selectedComparePersonality(article),
      getDetermination: () => safeOptionalInt(detInput.value),
      getLeadership: () => safeOptionalInt(leadInput.value),
      personalityFields: fields,
    },
  );

  if (!slotIsLinked(slot)) {
    const labelInput = article.querySelector<HTMLInputElement>(
      'input[data-field="label"]',
    )!;
    const squadList = article.querySelector<HTMLUListElement>(
      `ul[data-list="squad"]`,
    )!;
    bindCompareSquadNameCombo(slot, labelInput, squadList);
  }
}

function renderCompareSlots() {
  ensureCompareSlots();
  compareAddSlotEl.disabled = compareSlots.length >= COMPARE_MAX_SLOTS;
  compareSlotsEl.replaceChildren();

  compareSlots.forEach((slot) => {
    const article = document.createElement("article");
    article.className = "compare-slot";
    article.dataset.slotId = slot.id;
    const linked = slotIsLinked(slot);
    const nameBlock = linked
      ? `<div class="compare-player-chip">
          <span class="compare-player-chip-name">${escapeHtml(slot.label || "Player")}</span>
          <button
            type="button"
            class="compare-player-chip-clear"
            data-action="clear-player"
            title="Clear player"
            aria-label="Clear player"
          >×</button>
        </div>`
      : `<label class="combo-field compare-name-field">
          <span class="visually-hidden">Player name</span>
          <input
            class="compare-slot-label"
            type="text"
            data-field="label"
            maxlength="40"
            autocomplete="off"
            spellcheck="false"
            placeholder="Name or pick from Squad…"
            value="${escapeHtml(slot.label)}"
            role="combobox"
            aria-autocomplete="list"
            aria-controls="${slot.id}-squad-list"
            aria-expanded="false"
          />
          <ul
            id="${slot.id}-squad-list"
            class="combo-list"
            data-list="squad"
            hidden
            role="listbox"
          ></ul>
        </label>`;
    article.innerHTML = `
      <div class="compare-slot-top">
        ${nameBlock}
        <button
          type="button"
          class="compare-slot-remove"
          data-action="remove"
          title="Remove player"
          aria-label="Remove player"
          ${compareSlots.length <= COMPARE_MIN_SLOTS ? "disabled" : ""}
        >×</button>
      </div>
      <article class="ranker-podium-slot compare-slot-card" data-card-size="normal">
        <span class="ranker-place is-placeholder">#—</span>
        <p class="ranker-combo-name">—</p>
        <p class="ranker-combo-media">Pick personality / media</p>
        <div class="ranker-podium-meta"></div>
      </article>
      <div class="compare-slot-fields">
        <label class="combo-field compare-chip-field" data-field="personality">
          <span class="visually-hidden">Personality</span>
          <span class="field-warn" hidden aria-hidden="true">!</span>
          <span class="check-input-chip-face">
            <span class="check-input-chip-icon" title="Personality" aria-hidden="true">
              <span class="field-icon field-icon-personality"></span>
            </span>
            <input
              data-field="personality"
              type="text"
              autocomplete="off"
              spellcheck="false"
              placeholder="Personality"
              value="${escapeHtml(slot.personality)}"
              role="combobox"
              aria-autocomplete="list"
              aria-controls="${slot.id}-personality-list"
              aria-expanded="false"
              aria-label="Personality"
            />
          </span>
          <ul
            id="${slot.id}-personality-list"
            class="combo-list"
            data-list="personality"
            hidden
            role="listbox"
          ></ul>
        </label>
        <label class="combo-field compare-chip-field" data-field="mediaHandling">
          <span class="visually-hidden">Media handling</span>
          <span class="field-warn" hidden aria-hidden="true">!</span>
          <span class="check-input-chip-face">
            <span class="check-input-chip-icon" title="Media handling" aria-hidden="true">
              <span class="field-icon field-icon-media"></span>
            </span>
            <input
              data-field="mediaHandling"
              type="text"
              autocomplete="off"
              spellcheck="false"
              placeholder="Media"
              value="${escapeHtml(slot.mediaHandling)}"
              role="combobox"
              aria-autocomplete="list"
              aria-controls="${slot.id}-media-list"
              aria-expanded="false"
              aria-label="Media handling"
            />
          </span>
          <ul
            id="${slot.id}-media-list"
            class="combo-list"
            data-list="media"
            hidden
            role="listbox"
          ></ul>
        </label>
        <div class="compare-slot-known">
          <label class="compare-chip-field" data-field="determination">
            <span class="visually-hidden">Determination</span>
            <span class="check-input-chip-face">
              <span class="check-input-chip-icon" title="Determination" aria-hidden="true">
                <span class="field-icon field-icon-determination"></span>
              </span>
              <input data-field="determination" type="number" min="1" max="20" inputmode="numeric" value="${escapeHtml(slot.determination)}" placeholder="Det" aria-label="Determination" />
            </span>
          </label>
          <label class="compare-chip-field" data-field="leadership">
            <span class="visually-hidden">Leadership</span>
            <span class="check-input-chip-face">
              <span class="check-input-chip-icon" title="Leadership" aria-hidden="true">
                <span class="field-icon field-icon-leadership"></span>
              </span>
              <input data-field="leadership" type="number" min="1" max="20" inputmode="numeric" value="${escapeHtml(slot.leadership)}" placeholder="Lea" aria-label="Leadership" />
            </span>
          </label>
          <label class="compare-chip-field" data-field="age">
            <span class="visually-hidden">Age</span>
            <span class="check-input-chip-face">
              <span class="check-input-chip-icon" title="Age" aria-hidden="true">
                <span class="field-icon field-icon-age"></span>
              </span>
              <input data-field="age" type="number" min="15" max="45" inputmode="numeric" value="${escapeHtml(slot.age)}" placeholder="Age" aria-label="Age" />
            </span>
          </label>
        </div>
        <div class="regen-chip-field compare-slot-regen" data-field="isRegen">
          <input
            data-field="isRegen"
            class="visually-hidden"
            type="checkbox"
            tabindex="-1"
            ${slot.isRegen ? "checked" : ""}
          />
          <button
            type="button"
            class="ranker-pop regen-chip-toggle ${slot.isRegen ? "is-newgen" : "is-real"}"
            data-field="isRegen-chip"
            aria-pressed="${slot.isRegen}"
            aria-label="${slot.isRegen ? "NEWGEN — click for REAL" : "REAL — click for NEWGEN"}"
          >
            ${slot.isRegen ? "NEWGEN" : "REAL"}
          </button>
        </div>
      </div>
    `;
    compareSlotsEl.append(article);
    bindCompareSlotCombos(slot, article);
    const card = article.querySelector<HTMLElement>(".compare-slot-card");
    if (card) {
      setPodiumPopulationLabel(card, slot.isRegen ? "NEWGEN" : "REAL");
    }
  });
}

function estimateCompareSlot(slot: CompareSlotState): CompareSlotResult {
  const personality = slot.personality.trim();
  const media = slot.mediaHandling.trim();
  const personalityKnown = Boolean(findPersonality(catalog, personality));
  const mediaResolved = media
    ? (normalizeMatch(media, mediaStyles) ?? undefined)
    : undefined;
  if (!personalityKnown && !mediaResolved) {
    return { slotId: slot.id, result: null, tone: "neutral" };
  }
  try {
    const determination = parseOptionalInt(slot.determination);
    const leadership = parseOptionalInt(slot.leadership);
    const age = parseOptionalInt(slot.age);
    assertAttrInScale("Determination", determination);
    assertAttrInScale("Leadership", leadership);
    const personalityMatch = findPersonality(catalog, personality);
    const signals = {
      isRegen: slot.isRegen,
      ...(personalityKnown
        ? { personality: personalityMatch?.id ?? personality }
        : {}),
      ...(mediaResolved ? { mediaHandling: mediaResolved } : {}),
      ...(determination !== undefined ? { determination } : {}),
      ...(leadership !== undefined ? { leadership } : {}),
      ...(age !== undefined ? { age } : {}),
    };
    const result = estimatePlayer(catalog, signals);
    const visible = visibleKnownFromEstimate(result);
    const score = hiddenQualityScore(result.attributes, visible);
    const finite = Number.isFinite(score);
    const tone = finite
      ? hiddenQualityTone(score, catalogEliteHasFloor, catalogPoorHasCeiling)
      : "neutral";
    const rank =
      personalityKnown && mediaResolved
        ? lookupComboRank(
            personalityMatch?.id ?? personality,
            mediaResolved,
            slot.isRegen,
          )
        : undefined;
    return {
      slotId: slot.id,
      result,
      ...(finite ? { score } : {}),
      ...(rank !== undefined ? { rank } : {}),
      tone,
    };
  } catch (error) {
    return {
      slotId: slot.id,
      result: null,
      tone: "neutral",
      error: error instanceof Error ? error.message : "Estimate failed",
    };
  }
}

function updateCompareSlotMeta() {
  for (const article of compareSlotsEl.querySelectorAll<HTMLElement>(".compare-slot")) {
    const slotId = article.dataset.slotId;
    if (!slotId) continue;
    const slot = findCompareSlot(slotId);
    const entry = compareResults.find((row) => row.slotId === slotId);
    const card = article.querySelector<HTMLElement>(".compare-slot-card");
    const place = card?.querySelector<HTMLElement>(".ranker-place");
    const name = card?.querySelector<HTMLElement>(".ranker-combo-name");
    const media = card?.querySelector<HTMLElement>(".ranker-combo-media");
    const meta = card?.querySelector<HTMLElement>(".ranker-podium-meta");
    if (!slot || !card || !place || !name || !media || !meta) continue;

    const popLabel = slot.isRegen ? "NEWGEN" : "REAL";
    const personality =
      entry?.result?.player.personality?.trim() ||
      slot.personality.trim() ||
      "—";
    const mediaLabel =
      entry?.result?.player.mediaHandling?.trim() ||
      slot.mediaHandling.trim() ||
      "";

    card.classList.remove("is-good", "is-bad", "has-combo");
    place.classList.remove("is-good", "is-bad", "is-placeholder");

    if (!entry?.result || entry.score === undefined) {
      place.textContent = "#—";
      place.classList.add("is-placeholder");
      name.textContent = personality === "—" ? "—" : personality;
      media.textContent = mediaLabel || "Pick personality / media";
      meta.replaceChildren();
      setPodiumPopulationLabel(card, popLabel);
      card.removeAttribute("title");
      continue;
    }

    card.classList.add("has-combo");
    if (entry.tone === "good") card.classList.add("is-good");
    if (entry.tone === "bad") card.classList.add("is-bad");

    if (entry.rank !== undefined) {
      place.textContent = `#${entry.rank}`;
    } else {
      place.textContent = "#—";
      place.classList.add("is-placeholder");
    }
    if (entry.tone === "good") place.classList.add("is-good");
    if (entry.tone === "bad") place.classList.add("is-bad");

    name.textContent = personality;
    media.textContent = mediaLabel || "—";
    meta.replaceChildren(createHaBadge(entry.score, entry.tone));
    setPodiumPopulationLabel(card, popLabel);

    const weightsTip = formatHaQualityWeightsTip(
      visibleKnownFromEstimate(entry.result),
    );
    card.title =
      entry.rank !== undefined
        ? `Combo rank #${entry.rank} · elite ≥ ${formatHaScore(catalogEliteHasFloor)} · poor ≤ ${formatHaScore(catalogPoorHasCeiling)} · ${weightsTip}`
        : `Elite ≥ ${formatHaScore(catalogEliteHasFloor)} · poor ≤ ${formatHaScore(catalogPoorHasCeiling)} · ${weightsTip}`;
  }
}

function compareAttrPlotValue(estimate: {
  min: number;
  max: number;
  midpoint: number;
}): number {
  if (comparePlotMode === "min") return estimate.min;
  if (comparePlotMode === "max") return estimate.max;
  // Mid + Band: Δ uses the midpoint of the band.
  return estimate.midpoint;
}

/** Band for Compare matrix / radar — Det/Lea from entered or implied visibles. */
function compareAttrBand(
  result: EstimateResult | null | undefined,
  attribute: (typeof CHECKER_TABLE_ATTRIBUTES)[number],
): { min: number; max: number; midpoint: number } | null {
  if (!result) return null;
  if ((VISIBLE_ATTRIBUTES as readonly string[]).includes(attribute)) {
    const visible = attribute as VisibleAttribute;
    const entered =
      visible === "determination"
        ? result.player.determination
        : result.player.leadership;
    if (entered !== undefined) {
      return { min: entered, max: entered, midpoint: entered };
    }
    const implied = result.impliedVisible[visible];
    if (!implied) return null;
    return {
      min: implied.min,
      max: implied.max,
      midpoint: (implied.min + implied.max) / 2,
    };
  }
  const estimate = result.attributes[attribute as HasAttribute];
  if (
    !estimate ||
    estimate.unmodeled ||
    estimate.impossible ||
    estimate.min > estimate.max
  ) {
    return null;
  }
  return {
    min: estimate.min,
    max: estimate.max,
    midpoint: estimate.midpoint,
  };
}

function renderCompareMatrix() {
  const baselineSlot = compareSlots[0];
  const baselineResult = baselineSlot
    ? compareResults.find((row) => row.slotId === baselineSlot.id)
    : undefined;

  // One column per player: name header, with HA value + Δ centered beneath it.
  const colgroup = document.createElement("colgroup");
  const attrCol = document.createElement("col");
  attrCol.className = "compare-col-attr";
  colgroup.append(attrCol);
  for (const _slot of compareSlots) {
    const playerCol = document.createElement("col");
    playerCol.className = "compare-col-player";
    colgroup.append(playerCol);
  }

  const headRow = document.createElement("tr");
  const attrTh = document.createElement("th");
  attrTh.textContent = "Attribute";
  attrTh.scope = "col";
  headRow.append(attrTh);
  compareSlots.forEach((slot, index) => {
    const th = document.createElement("th");
    th.scope = "col";
    const name = slotDisplayName(slot, index);
    th.textContent = name;
    th.title = name;
    th.className = "compare-player-col";
    headRow.append(th);
  });
  compareMatrixHeadEl.replaceChildren(headRow);

  const table = compareMatrixBodyEl.closest("table");
  if (table) {
    table.querySelector("colgroup")?.remove();
    table.insertBefore(colgroup, table.firstChild);
  }

  compareMatrixBodyEl.replaceChildren();
  for (const attribute of COMPARE_RADAR_ATTRS) {
    const tr = document.createElement("tr");
    tr.dataset.attribute = attribute;
    const nameTd = document.createElement("td");
    nameTd.innerHTML = `<span class="attr-name" title="${ATTRIBUTE_DESCRIPTIONS[attribute]}">${ATTRIBUTE_LABELS[attribute]}</span>`;
    tr.append(nameTd);

    const baselineEstimate = compareAttrBand(baselineResult?.result, attribute);
    const baselineValue = baselineEstimate
      ? compareAttrPlotValue(baselineEstimate)
      : undefined;

    for (const [slotIndex, slot] of compareSlots.entries()) {
      const td = document.createElement("td");
      td.className = "compare-player-cell";
      if (slotIndex === 0) td.classList.add("is-baseline");

      const pair = document.createElement("span");
      pair.className = "compare-pair";

      const valEl = document.createElement("span");
      valEl.className = "compare-val fmt-mid is-empty";
      valEl.textContent = "—";

      const deltaEl = document.createElement("span");
      deltaEl.className = "compare-delta is-empty";
      deltaEl.setAttribute("aria-hidden", "true");

      const entry = compareResults.find((row) => row.slotId === slot.id);
      const estimate = compareAttrBand(entry?.result, attribute);
      if (!estimate) {
        pair.append(valEl, deltaEl);
        td.append(pair);
        tr.append(td);
        continue;
      }

      const mid = estimate.midpoint;
      const tone = attributeTone(attribute, mid);
      const value = compareAttrPlotValue(estimate);
      const valueText =
        comparePlotMode === "band"
          ? formatBandCell(estimate)
          : comparePlotMode === "min" || comparePlotMode === "max"
            ? String(Math.round(value))
            : formatMidCell(value);

      valEl.textContent = valueText;
      valEl.className = [
        "compare-val",
        comparePlotMode === "band" ? "fmt-band" : "fmt-mid",
        tone === "good" ? "good" : "",
        tone === "bad" ? "bad" : "",
      ]
        .filter(Boolean)
        .join(" ");

      if (
        slotIndex > 0 &&
        baselineValue !== undefined &&
        Number.isFinite(baselineValue)
      ) {
        const delta = value - baselineValue;
        if (Math.abs(delta) >= 0.05) {
          const signed = formatClimbDelta(delta);
          const quality = compareAttrDeltaQualityClass(attribute, delta);
          deltaEl.textContent = signed;
          deltaEl.className = ["compare-delta", quality].filter(Boolean).join(" ");
          deltaEl.removeAttribute("aria-hidden");
          const vs = slotDisplayName(compareSlots[0]!, 0);
          deltaEl.title =
            attribute === "controversy"
              ? `${signed} vs ${vs} (lower Controversy is better)`
              : `${signed} vs ${vs}`;
        }
      }

      pair.append(valEl, deltaEl);
      td.append(pair);
      tr.append(td);
    }

    compareMatrixBodyEl.append(tr);
  }
}

function syncCompareViewChrome() {
  for (const btn of compareViewModeEl.querySelectorAll<HTMLButtonElement>(
    ".compare-view-btn",
  )) {
    const active = btn.dataset.compareView === compareViewMode;
    btn.setAttribute("aria-pressed", String(active));
  }
  comparePlotModeEl.value = comparePlotMode;
  const showGraph = compareViewMode === "graph";
  compareMatrixScrollEl.hidden = showGraph;
  compareRadarWrapEl.hidden = !showGraph;
}

function radarPlotValue(attribute: TrackedAttribute, raw: number): number {
  const clamped = Math.min(20, Math.max(1, raw));
  // Outer = better: invert Controversy so high Contro stays near center.
  return attribute === "controversy" ? 21 - clamped : clamped;
}

function radarPoint(
  index: number,
  total: number,
  value: number,
  cx: number,
  cy: number,
  radius: number,
): { x: number; y: number } {
  const angle = -Math.PI / 2 + (index / total) * Math.PI * 2;
  const t = (Math.min(20, Math.max(1, value)) - 1) / 19;
  const r = t * radius;
  return { x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r };
}

function svgEl<K extends keyof SVGElementTagNameMap>(
  name: K,
  attrs: Record<string, string | number> = {},
): SVGElementTagNameMap[K] {
  const el = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attrs)) {
    el.setAttribute(key, String(value));
  }
  return el;
}

function renderCompareRadar() {
  const size = 420;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 148;
  const n = COMPARE_RADAR_ATTRS.length;
  compareRadarEl.replaceChildren();
  compareRadarLegendEl.replaceChildren();

  const rings = svgEl("g", { class: "compare-radar-rings" });
  for (const level of [5, 10, 15, 20]) {
    const pts = COMPARE_RADAR_ATTRS.map((_, i) => {
      const p = radarPoint(i, n, level, cx, cy, radius);
      return `${p.x.toFixed(1)},${p.y.toFixed(1)}`;
    }).join(" ");
    rings.append(
      svgEl("polygon", {
        class: "compare-radar-grid",
        points: pts,
      }),
    );
  }
  compareRadarEl.append(rings);

  const axes = svgEl("g", { class: "compare-radar-axes" });
  COMPARE_RADAR_ATTRS.forEach((attribute, i) => {
    const tip = radarPoint(i, n, 20, cx, cy, radius);
    axes.append(
      svgEl("line", {
        class: "compare-radar-axis",
        x1: cx,
        y1: cy,
        x2: tip.x.toFixed(1),
        y2: tip.y.toFixed(1),
      }),
    );
    const labelR = radius + 28;
    const labelAngle = -Math.PI / 2 + (i / n) * Math.PI * 2;
    const lx = cx + Math.cos(labelAngle) * labelR;
    const ly = cy + Math.sin(labelAngle) * labelR;
    const label = svgEl("text", {
      class: "compare-radar-label",
      x: lx.toFixed(1),
      y: ly.toFixed(1),
      dy: "0.35em",
    });
    label.textContent = ATTRIBUTE_LABELS[attribute];
    axes.append(label);
  });
  compareRadarEl.append(axes);

  const series = svgEl("g", { class: "compare-radar-series" });
  compareSlots.forEach((slot, slotIndex) => {
    const entry = compareResults.find((row) => row.slotId === slot.id);
    const color = COMPARE_RADAR_COLORS[slotIndex % COMPARE_RADAR_COLORS.length]!;
    const mids: number[] = [];
    const mins: number[] = [];
    const maxes: number[] = [];
    let any = false;
    for (const attribute of COMPARE_RADAR_ATTRS) {
      const band = compareAttrBand(entry?.result, attribute);
      if (!band) {
        mids.push(1);
        mins.push(1);
        maxes.push(1);
        continue;
      }
      any = true;
      mids.push(radarPlotValue(attribute, band.midpoint));
      mins.push(radarPlotValue(attribute, band.min));
      maxes.push(radarPlotValue(attribute, band.max));
    }
    if (!any) return;

    const drawPoly = (values: number[], className: string, filled: boolean) => {
      const pts = values
        .map((value, i) => {
          const p = radarPoint(i, n, value, cx, cy, radius);
          return `${p.x.toFixed(1)},${p.y.toFixed(1)}`;
        })
        .join(" ");
      series.append(
        svgEl("polygon", {
          class: className,
          points: pts,
          fill: filled ? color.fill : "none",
          stroke: color.stroke,
        }),
      );
      values.forEach((value, i) => {
        const p = radarPoint(i, n, value, cx, cy, radius);
        series.append(
          svgEl("circle", {
            class: "compare-radar-dot",
            cx: p.x.toFixed(1),
            cy: p.y.toFixed(1),
            r: 3.2,
            fill: color.stroke,
          }),
        );
      });
    };

    if (comparePlotMode === "min") {
      drawPoly(mins, "compare-radar-poly", true);
    } else if (comparePlotMode === "max") {
      drawPoly(maxes, "compare-radar-poly", true);
    } else if (comparePlotMode === "band") {
      drawPoly(maxes, "compare-radar-poly is-ceil", false);
      drawPoly(mins, "compare-radar-poly is-floor", false);
    } else {
      drawPoly(mids, "compare-radar-poly", true);
    }

    // Value readout near vertices for the primary plot series (single player only).
    if (compareSlots.filter((s) =>
      compareResults.some((row) => row.slotId === s.id && row.result),
    ).length === 1) {
      const primary =
        comparePlotMode === "min"
          ? mins
          : comparePlotMode === "max"
            ? maxes
            : mids;
      primary.forEach((_value, i) => {
        const p = radarPoint(i, n, Math.min(20, primary[i]! + 1.4), cx, cy, radius);
        const text = svgEl("text", {
          class: "compare-radar-value",
          x: p.x.toFixed(1),
          y: p.y.toFixed(1),
          dy: "-0.35em",
        });
        const attr = COMPARE_RADAR_ATTRS[i]!;
        const band = entry?.result?.attributes[attr];
        if (!band) return;
        const shown =
          comparePlotMode === "band"
            ? formatBandCell(band).trim()
            : comparePlotMode === "min"
              ? String(Math.round(band.min))
              : comparePlotMode === "max"
                ? String(Math.round(band.max))
                : String(Math.round(band.midpoint * 10) / 10);
        text.textContent = shown;
        series.append(text);
      });
    }

    const li = document.createElement("li");
    const swatch = document.createElement("span");
    swatch.className = "compare-radar-swatch";
    swatch.style.background = color.stroke;
    const name = document.createElement("span");
    name.textContent = slotDisplayName(slot, slotIndex);
    li.append(swatch, name);
    compareRadarLegendEl.append(li);
  });
  compareRadarEl.append(series);
}

function runCompareEstimates() {
  ensureCompareSlots();
  persistCompareDraft();
  compareResults = compareSlots.map((slot) => estimateCompareSlot(slot));
  const errors = compareResults
    .map((row) => row.error)
    .filter((msg): msg is string => Boolean(msg));
  if (errors.length) {
    compareStatusEl.hidden = false;
    compareStatusEl.textContent = errors[0]!;
  } else {
    compareStatusEl.hidden = true;
    compareStatusEl.textContent = "";
  }
  updateCompareSlotMeta();
  renderCompareMatrix();
  renderCompareRadar();
  syncCompareViewChrome();
}

compareSlotsEl.addEventListener("click", (event) => {
  const target = event.target as HTMLElement;
  const slotEl = target.closest<HTMLElement>(".compare-slot");
  if (!slotEl || !compareSlotsEl.contains(slotEl)) return;
  const slotId = slotEl.dataset.slotId;
  if (!slotId) return;
  const slot = findCompareSlot(slotId);
  if (!slot) return;

  const removeBtn = target.closest<HTMLButtonElement>('[data-action="remove"]');
  if (removeBtn) {
    if (compareSlots.length <= COMPARE_MIN_SLOTS) return;
    compareSlots = compareSlots.filter((row) => row.id !== slotId);
    renderCompareSlots();
    runCompareEstimates();
    return;
  }

  const clearBtn = target.closest<HTMLButtonElement>(
    '[data-action="clear-player"]',
  );
  if (clearBtn) {
    clearCompareSlotPlayer(slot);
    renderCompareSlots();
    runCompareEstimates();
  }
});

compareSlotsEl.addEventListener("change", (event) => {
  const target = event.target as HTMLElement;
  const slotEl = target.closest<HTMLElement>(".compare-slot");
  if (!slotEl || !compareSlotsEl.contains(slotEl)) return;
  const slotId = slotEl.dataset.slotId;
  const slot = slotId ? findCompareSlot(slotId) : undefined;
  if (!slot) return;
  syncCompareSlotFromDom(slotEl);
  if (slotIsLinked(slot)) syncLinkedComparePlayer(slot);
  runCompareEstimates();
});

compareSlotsEl.addEventListener("input", (event) => {
  const target = event.target as HTMLElement;
  if (!(target instanceof HTMLInputElement)) return;
  // Name/personality/media combos handle their own commit paths.
  if (
    target.dataset.field === "label" ||
    target.dataset.field === "personality" ||
    target.dataset.field === "mediaHandling"
  ) {
    return;
  }
  const slotEl = target.closest<HTMLElement>(".compare-slot");
  if (!slotEl || !compareSlotsEl.contains(slotEl)) return;
  const slotId = slotEl.dataset.slotId;
  const slot = slotId ? findCompareSlot(slotId) : undefined;
  syncCompareSlotFromDom(slotEl);
  if (slot && slotIsLinked(slot)) syncLinkedComparePlayer(slot);
  runCompareEstimates();
});

compareAddSlotEl.addEventListener("click", () => {
  ensureCompareSlots();
  if (compareSlots.length >= COMPARE_MAX_SLOTS) return;
  compareSlots.push(emptyCompareSlot());
  renderCompareSlots();
  runCompareEstimates();
});

compareViewModeEl.addEventListener("click", (event) => {
  const btn = (event.target as HTMLElement).closest<HTMLButtonElement>(
    ".compare-view-btn",
  );
  if (!btn || !compareViewModeEl.contains(btn)) return;
  const mode = btn.dataset.compareView;
  if (mode !== "table" && mode !== "graph") return;
  compareViewMode = mode;
  syncCompareViewChrome();
  if (compareViewMode === "graph") renderCompareRadar();
});

checkViewModeEl.addEventListener("click", (event) => {
  const btn = (event.target as HTMLElement).closest<HTMLButtonElement>(
    ".check-view-btn",
  );
  if (!btn || !checkViewModeEl.contains(btn)) return;
  const mode = btn.dataset.checkView;
  if (mode !== "table" && mode !== "plot") return;
  checkViewMode = mode;
  syncCheckViewChrome();
  if (checkViewMode === "plot") renderCheckRadar(lastCheckEstimateResult);
});

comparePlotModeEl.addEventListener("change", () => {
  const mode = comparePlotModeEl.value;
  if (!isComparePlotMode(mode)) return;
  comparePlotMode = mode;
  syncCompareViewChrome();
  renderCompareMatrix();
  renderCompareRadar();
});

function dash(value: string | number | undefined | null): string {
  if (value === undefined || value === null || value === "") return "—";
  return String(value);
}

function formatClubLine(
  clubName: string | null | undefined,
  clubId: number | null | undefined,
): string | null {
  const name = (clubName ?? "").trim();
  if (!name || clubId == null) return null;
  return `${name} ${clubId}`;
}

function formatUploadedAt(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

/** Compact extract timestamp for Manage Saves rows. */
function formatUploadedAtRow(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** In-game date from extract (`YYYY-MM-DD`) for the Career Save card. */
function formatInGameDate(isoDate: string | null | undefined): string {
  if (!isoDate) return "—";
  const d = new Date(`${isoDate}T12:00:00`);
  if (Number.isNaN(d.getTime())) return isoDate;
  return d.toLocaleDateString(undefined, { dateStyle: "medium" });
}

/** Compact in-game date for Manage Saves rows. */
function formatInGameDateRow(isoDate: string | null | undefined): string {
  if (!isoDate) return "—";
  const d = new Date(`${isoDate}T12:00:00`);
  if (Number.isNaN(d.getTime())) return isoDate;
  return d.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function setRosterSavesMenuOpen(open: boolean) {
  rosterSavesMenuOpen = open;
  rosterSavesMenuEl.hidden = !open;
  rosterSavesBtnEl.setAttribute("aria-expanded", open ? "true" : "false");
}

function syncRosterSavesMenu() {
  const names = listRosterSaveNames(rosterStore);
  rosterSavesCountEl.textContent = String(names.length);
  rosterSavesListEl.replaceChildren();
  rosterSavesEmptyEl.hidden = names.length > 0;

  // Drop stale overwrite slot if the save was removed.
  if (rosterAmendTarget && !rosterStore.saves[rosterAmendTarget]) {
    rosterAmendTarget = null;
  }

  for (const name of names) {
    const entry = rosterStore.saves[name]!;
    const club = entry.clubName || entry.clubNameShort;
    const id = entry.clubId ?? entry.teamId;
    const clubLine =
      club && id != null ? formatClubLine(club, id) : club || name;
    const isActive = name === rosterStore.activeSaveName;
    const isOverwrite = name === rosterAmendTarget;
    const diskLinked = rosterSaveDiskLinked(name);

    const row = document.createElement("div");
    row.className = "roster-saves-row";
    row.dataset.saveName = name;
    if (isActive) row.classList.add("is-active");
    if (isOverwrite) row.classList.add("is-overwrite");

    const uploaded = formatUploadedAtRow(entry.extractedAt);
    const inGame = formatInGameDateRow(entry.gameDate);

    const selectBtn = document.createElement("button");
    selectBtn.type = "button";
    selectBtn.className = "roster-saves-item";
    selectBtn.dataset.action = "select";
    selectBtn.dataset.saveName = name;
    selectBtn.title = [
      name,
      `Uploaded ${formatUploadedAt(entry.extractedAt)}`,
      `In-game ${formatInGameDate(entry.gameDate)}`,
    ].join("\n");
    selectBtn.innerHTML = `
      <span class="roster-saves-item-club">${escapeHtml(clubLine ?? name)}${
        isActive
          ? `<span class="roster-saves-item-badge">Active</span>`
          : ""
      }</span>
      <span class="roster-saves-item-file">${escapeHtml(name)}${
        diskLinked ? " · disk-linked" : ""
      }${
        isOverwrite ? " · next upload overwrites" : ""
      }</span>
      <span class="roster-saves-item-dates" aria-label="Uploaded ${escapeHtml(uploaded)}, in-game ${escapeHtml(inGame)}">
        <span class="roster-saves-item-date is-uploaded">
          <span class="roster-saves-item-date-label">Uploaded</span>
          <span class="roster-saves-item-date-value">${escapeHtml(uploaded)}</span>
        </span>
        <span class="roster-saves-item-date is-ingame">
          <span class="roster-saves-item-date-label">In-game</span>
          <span class="roster-saves-item-date-value">${escapeHtml(inGame)}</span>
        </span>
      </span>
    `;

    const actions = document.createElement("div");
    actions.className = "roster-saves-row-actions";

    const updateBtn = document.createElement("button");
    updateBtn.type = "button";
    updateBtn.className = "roster-saves-row-btn";
    updateBtn.dataset.action = "update";
    updateBtn.dataset.saveName = name;
    updateBtn.textContent = "Update";
    updateBtn.title = diskLinked
      ? "Re-read this save from disk (FM games folder)"
      : "Replace this extract — opens file picker if not found on disk";

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "roster-saves-row-btn is-danger";
    deleteBtn.dataset.action = "delete";
    deleteBtn.dataset.saveName = name;
    deleteBtn.textContent = "Delete";
    deleteBtn.title = "Permanently remove this extract";

    actions.append(updateBtn, deleteBtn);
    row.append(selectBtn, actions);
    rosterSavesListEl.append(row);
  }
}

function estimatesFromPersonalitySignals(
  pa: PersonalitySignals,
): { estimates: AttributeEstimates; visible: HaVisibleKnown } | null {
  const estimates = {} as AttributeEstimates;
  for (const attribute of HAS_ATTRIBUTES) {
    if (isUnmodeledHiddenAttribute(attribute)) {
      estimates[attribute] = {
        min: FULL_RANGE.min,
        max: FULL_RANGE.max,
        midpoint: Number.NaN,
        exact: false,
        unmodeled: true,
      };
      continue;
    }
    const raw = pa[attribute as keyof PersonalitySignals];
    if (raw == null || !Number.isFinite(raw)) return null;
    const value = Math.round(raw);
    if (value < FULL_RANGE.min || value > FULL_RANGE.max) return null;
    estimates[attribute] = toEstimate({ min: value, max: value });
  }
  const visible: HaVisibleKnown = {};
  if (pa.determination != null && Number.isFinite(pa.determination)) {
    visible.determination = pa.determination;
  }
  if (pa.leadership != null && Number.isFinite(pa.leadership)) {
    visible.leadership = pa.leadership;
  }
  return { estimates, visible };
}

/** Same weighted order as the attributes probe / HAS rank columns. */
const SQUAD_TIP_ATTRIBUTES = CHECKER_TABLE_ATTRIBUTES;

function toneClassForAttr(
  attribute: (typeof SQUAD_TIP_ATTRIBUTES)[number],
  value: number | null | undefined,
): string {
  if (value == null || !Number.isFinite(value)) return "is-empty";
  const tone = attributeTone(attribute, value);
  return tone === "neutral" ? "" : tone;
}

function buildSquadAttrsTip(
  pa: PersonalitySignals,
  combo: ComboRankEntry | null,
): HTMLElement {
  const panel = document.createElement("div");
  panel.className = "squad-attr-tip";

  const head = document.createElement("div");
  head.className = "squad-attr-tip-row is-head";
  for (const label of ["Attr", "In-game", "Band", "Mid"]) {
    const cell = document.createElement("span");
    cell.textContent = label;
    head.append(cell);
  }
  panel.append(head);

  for (const attr of SQUAD_TIP_ATTRIBUTES) {
    const row = document.createElement("div");
    row.className = "squad-attr-tip-row";

    const name = document.createElement("span");
    name.className = "squad-attr-tip-name";
    name.textContent = PERSONALITY_ATTRIBUTE_ABBR[attr];
    name.title = PERSONALITY_ATTRIBUTE_LABELS[attr];

    const value = pa[attr];
    const valueEl = document.createElement("span");
    valueEl.className = "squad-attr-tip-val";
    if (value == null || !Number.isFinite(value)) {
      valueEl.textContent = "—";
      valueEl.classList.add("is-empty");
    } else {
      valueEl.textContent = formatAttrNumber(value);
      const tone = toneClassForAttr(attr, value);
      if (tone) valueEl.classList.add(tone);
    }

    const band = combo?.bands[attr] ?? null;
    const bandEl = document.createElement("span");
    bandEl.className = "squad-attr-tip-val is-band";
    if (!band) {
      bandEl.textContent = "—";
      bandEl.classList.add("is-empty");
    } else {
      bandEl.textContent = formatBandCell(band);
      const midForTone = (band.min + band.max) / 2;
      const tone = toneClassForAttr(attr, midForTone);
      if (tone) bandEl.classList.add(tone);
    }

    const midRaw = combo?.mids[attr] ?? null;
    const midEl = document.createElement("span");
    midEl.className = "squad-attr-tip-val is-mid";
    if (midRaw == null || !Number.isFinite(midRaw)) {
      midEl.textContent = "—";
      midEl.classList.add("is-empty");
    } else {
      midEl.textContent = formatSquadTipMid(midRaw);
      const tone = toneClassForAttr(attr, midRaw);
      if (tone) midEl.classList.add(tone);
    }

    row.append(name, valueEl, bandEl, midEl);
    panel.append(row);
  }

  return panel;
}

const SQUAD_MATCH_ATTRS = [
  "determination",
  "leadership",
  "ambition",
  "controversy",
  "loyalty",
  "pressure",
  "professionalism",
  "sportsmanship",
  "temperament",
] as const satisfies ReadonlyArray<keyof PersonalitySignals>;

/**
 * Locate the personality × media map piece that contains the player's attrs.
 *
 * Uses case-feasible point matching (not union-projected mid bands) so stricter
 * media styles (Level-Headed, Unflappable) win over looser Media-friendly
 * overlaps. Sheet `prioritizedBy` then drops personality losers; remaining
 * ties break on tightest non-full bands then catalog rank.
 */
function matchPersonalityComboFromAttrs(
  pa: PersonalitySignals,
  opts?: { isRegen?: boolean; age?: number },
): ComboRankEntry | null {
  if (lastRankerEntries.length === 0) {
    renderPersonalityRanker();
  }

  const attrs = {
    ...Object.fromEntries(
      SQUAD_MATCH_ATTRS.map((key) => [key, pa[key]] as const),
    ),
    ...(opts?.isRegen !== undefined ? { isRegen: opts.isRegen } : {}),
    ...(opts?.age !== undefined ? { age: opts.age } : {}),
  };

  const hits: ComboRankEntry[] = [];
  for (const entry of lastRankerEntries) {
    // Keep REAL/NEWGEN ladder rows on the matching population when known.
    if (opts?.isRegen === true && entry.label === "REAL") continue;
    if (opts?.isRegen === false && entry.label === "NEWGEN") continue;
    if (
      comboFeasibleForAttrs(
        catalog,
        entry.personality,
        entry.mediaHandling,
        attrs,
      )
    ) {
      hits.push(entry);
    }
  }
  if (hits.length === 0) return null;
  if (hits.length === 1) return hits[0]!;

  // Drop personality losers via sheet priority (A wins over B if A ∈ B.prioritizedBy).
  const personalities = new Set(hits.map((h) => h.personality));
  const winners = new Set(personalities);
  for (const id of personalities) {
    const def = findPersonality(catalog, id);
    if (!def) continue;
    for (const better of def.prioritizedBy) {
      if (personalities.has(better)) {
        winners.delete(id);
        break;
      }
    }
  }
  const priorityHits = hits.filter((h) => winners.has(h.personality));
  const pool = priorityHits.length > 0 ? priorityHits : hits;

  // Still ambiguous (usually media): prefer the tightest non-full bands.
  let best: ComboRankEntry | null = null;
  let bestTight = Number.POSITIVE_INFINITY;
  for (const entry of pool) {
    let tight = 0;
    for (const key of SQUAD_MATCH_ATTRS) {
      const band = entry.bands[key];
      if (
        !band ||
        (band.min === FULL_RANGE.min && band.max === FULL_RANGE.max)
      ) {
        continue;
      }
      tight += band.max - band.min;
    }
    if (
      !best ||
      tight < bestTight ||
      (tight === bestTight && entry.rank < best.rank)
    ) {
      best = entry;
      bestTight = tight;
    }
  }
  return best;
}

function midMedalVsComboHas(
  score: number,
  midHas: number,
): "gold" | "silver" | "bronze" {
  if (score > midHas + 1e-9) return "gold";
  if (score < midHas - 1e-9) return "bronze";
  return "silver";
}

/** Load `/api/faces/:uid` with retries. Never start as display:none — browsers skip those fetches. */
function bindPlayerFace(
  img: HTMLImageElement,
  uid: number | string,
  options?: {
    onReady?: () => void;
    onMissing?: () => void;
    maxAttempts?: number;
  },
): void {
  const maxAttempts = options?.maxAttempts ?? 3;
  let attempt = 0;
  let settled = false;

  const markReady = () => {
    if (settled) return;
    settled = true;
    img.classList.add("is-ready");
    img.classList.remove("is-missing");
    options?.onReady?.();
  };

  const markMissing = () => {
    if (settled) return;
    settled = true;
    img.classList.remove("is-ready");
    img.classList.add("is-missing");
    img.removeAttribute("src");
    options?.onMissing?.();
  };

  const load = () => {
    attempt += 1;
    // First attempt only: clear ready state. Retries keep the prior frame
    // (or letter fallback) so faces don't skeleton-flash.
    if (attempt === 1) {
      img.classList.remove("is-missing", "is-ready");
    }
    const url = `/api/faces/${uid}?t=${attempt}`;
    if (attempt === 1) {
      img.src = url;
      return;
    }
    const probe = new Image();
    probe.decoding = "async";
    probe.onload = () => {
      img.src = url;
      markReady();
    };
    probe.onerror = () => {
      if (attempt < maxAttempts) {
        window.setTimeout(load, 250 * attempt);
        return;
      }
      markMissing();
    };
    probe.src = url;
  };

  img.addEventListener("load", markReady);
  img.addEventListener("error", () => {
    if (attempt < maxAttempts) {
      window.setTimeout(load, 250 * attempt);
      return;
    }
    markMissing();
  });

  load();
}

/** Load `/api/logos/:clubId` — TCM megapack club crest. */
function bindClubLogo(
  img: HTMLImageElement,
  clubId: number,
  options?: {
    onReady?: () => void;
    onMissing?: () => void;
    maxAttempts?: number;
  },
): void {
  const maxAttempts = options?.maxAttempts ?? 2;
  let attempt = 0;
  let settled = false;

  const markReady = () => {
    if (settled) return;
    settled = true;
    img.classList.add("is-ready");
    img.classList.remove("is-missing");
    options?.onReady?.();
  };

  const markMissing = () => {
    if (settled) return;
    settled = true;
    img.classList.remove("is-ready");
    img.classList.add("is-missing");
    img.removeAttribute("src");
    options?.onMissing?.();
  };

  const load = () => {
    attempt += 1;
    if (attempt === 1) {
      img.classList.remove("is-ready", "is-missing");
    }
    img.onload = () => markReady();
    img.onerror = () => {
      if (attempt < maxAttempts) {
        window.setTimeout(load, 100 * attempt);
        return;
      }
      markMissing();
    };
    img.src = `/api/logos/${clubId}?t=${attempt}`;
  };

  load();
}

function createSquadPersonalityCard(
  player: RosterPlayer,
  score: number | null,
): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "squad-card-wrap";
  wrap.setAttribute("role", "listitem");

  const trust = playerExtractTrust(player);
  const resolvedName = rosterResolvedName(player);
  const pa = rosterPersonalitySignals(player);
  const age = rosterPlayerAge(player, rosterMeta.gameDate);
  const combo =
    trust.attrsEnough && pa
      ? matchPersonalityComboFromAttrs(pa, {
          isRegen: player.kind === "NEWGEN",
          ...(age != null ? { age } : {}),
        })
      : null;
  const displayScore =
    trust.attrsEnough && score != null && Number.isFinite(score) ? score : null;

  const slot = document.createElement("article");
  slot.className = "ranker-podium-slot check-combo-card squad-player-card";
  slot.dataset.cardSize = "small";

  const midRankClasses = ["is-mid-gold", "is-mid-silver", "is-mid-bronze"] as const;
  const place = document.createElement("span");
  place.className = "ranker-place";

  const personalityEl = document.createElement("p");
  personalityEl.className = "ranker-combo-name";

  const mediaEl = document.createElement("p");
  mediaEl.className = "ranker-combo-media";

  const meta = document.createElement("div");
  meta.className = "ranker-podium-meta check-combo-meta";

  if (!trust.mentoringReady) {
    wrap.classList.add("is-incomplete");
    slot.classList.add("is-incomplete");
    place.textContent = "—";
    place.classList.add("is-placeholder");
    personalityEl.textContent = "Incomplete extract";
    const holes = extractTrustHoles(trust).filter(
      (hole) => hole !== "loan unclassified",
    );
    mediaEl.textContent = holes.join(" · ") || "Incomplete";
    const missing = document.createElement("span");
    missing.className = "ranker-ha is-empty";
    missing.textContent = displayScore != null ? formatHaScore(displayScore) : "No HAS";
    meta.append(missing);
    slot.title = [
      "Incomplete extract — not mentoring-ready",
      ...extractTrustHoles(trust),
      "Personality is inferred from attrs, not read as FM text",
    ].join("\n");
  } else if (displayScore != null && combo) {
    const tone = hiddenQualityTone(
      displayScore,
      catalogEliteHasFloor,
      catalogPoorHasCeiling,
    );
    const medal = midMedalVsComboHas(displayScore, combo.haScore);

    slot.classList.add("has-combo");
    slot.classList.toggle("is-good", tone === "good");
    slot.classList.toggle("is-bad", tone === "bad");

    place.textContent = `#${combo.rank}`;
    place.classList.remove("is-placeholder", "is-good", "is-bad", ...midRankClasses);
    place.classList.add(
      medal === "gold"
        ? "is-mid-gold"
        : medal === "bronze"
          ? "is-mid-bronze"
          : "is-mid-silver",
    );

    personalityEl.textContent = combo.personality;
    mediaEl.textContent = combo.mediaHandling;
    meta.append(createHaBadge(displayScore, tone));

    const medalTip =
      medal === "gold"
        ? "above personality mid HAS"
        : medal === "bronze"
          ? "below personality mid HAS"
          : "on personality mid HAS";
    slot.title = [
      `${combo.personality} · ${combo.mediaHandling}`,
      `Catalog #${combo.rank} · mid HAS ${formatHaScore(combo.haScore)}`,
      `Save HAS ${formatHaScore(displayScore)} (${medalTip})`,
      "Personality inferred from attrs (not FM text)",
    ].join("\n");
  } else if (displayScore != null) {
    const tone = hiddenQualityTone(
      displayScore,
      catalogEliteHasFloor,
      catalogPoorHasCeiling,
    );
    slot.classList.add("has-combo");
    slot.classList.toggle("is-good", tone === "good");
    slot.classList.toggle("is-bad", tone === "bad");
    place.textContent = "—";
    place.classList.add("is-placeholder");
    personalityEl.textContent = "Unknown personality";
    mediaEl.textContent = "No combo contains these attrs";
    meta.append(createHaBadge(displayScore, tone));
    slot.title = `Save HAS ${formatHaScore(displayScore)} · attrs fall outside every personality × media band set`;
  } else {
    place.textContent = "—";
    place.classList.add("is-placeholder");
    personalityEl.textContent = "No personality data";
    mediaEl.textContent = "Re-upload Career Save";
    const missing = document.createElement("span");
    missing.className = "ranker-ha is-empty";
    missing.textContent = "No HAS";
    meta.append(missing);
    slot.title = "Missing attributes.general / mental Det·Lea — re-upload the Career Save";
  }

  slot.append(place, personalityEl, mediaEl, meta);
  wrap.append(slot);

  const name = document.createElement("span");
  name.className = "squad-player-name";
  name.textContent = resolvedName ?? "Name missing";
  if (!resolvedName) name.title = player.name?.trim() || `uid:${player.uid}`;

  const badge = document.createElement("span");
  badge.className = "squad-player-badge has-no-face";

  const face = document.createElement("img");
  face.className = "squad-player-face";
  face.alt = "";
  face.decoding = "async";
  bindPlayerFace(face, player.uid, {
    onReady: () => badge.classList.remove("has-no-face"),
    onMissing: () => badge.classList.add("has-no-face"),
  });

  badge.append(face, name);

  const loanClubId = playerLoanBadgeClubId(player);
  if (loanClubId != null) {
    wrap.classList.add(
      player.loan?.status === "loanedOut" ? "is-loaned-out" : "is-loaned-in",
    );
    const crest = document.createElement("img");
    crest.className = "squad-loan-crest";
    crest.alt = playerLoanBadgeLabel(player) ?? "";
    crest.decoding = "async";
    crest.title =
      player.loan?.status === "loanedOut"
        ? `On loan at ${playerLoanBadgeLabel(player) ?? "loan club"}`
        : `On loan from ${playerLoanBadgeLabel(player) ?? "parent club"}`;
    bindClubLogo(crest, loanClubId, {
      onMissing: () => crest.remove(),
    });
    badge.append(crest);
  }

  wrap.append(badge);

  wrap.classList.add("is-clickable");
  wrap.tabIndex = 0;
  wrap.setAttribute(
    "aria-label",
    `${resolvedName ?? "Name missing"}, open attribute history`,
  );
  const openAttrs = () => {
    // From Loans (or other non-unit tabs), land on the unit that owns the player
    // so the attributes picker still lists them.
    if (!isSquadUnitMode(squadViewMode)) {
      if (reservesPlayers.some((p) => p.uid === player.uid)) {
        squadViewMode = "reserves";
      } else if (under19sPlayers.some((p) => p.uid === player.uid)) {
        squadViewMode = "under19s";
      } else {
        squadViewMode = "firstTeam";
      }
    }
    selectSquadEvolutionPlayer(player.uid);
    setSquadUnitView("attributes");
  };
  wrap.addEventListener("click", openAttrs);
  wrap.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    openAttrs();
  });

  return wrap;
}

function renderRoster() {
  rosterBodyEl.replaceChildren();
  syncRosterSavesMenu();

  const hasSave = rosterMeta.source === "save" && Boolean(rosterMeta.saveName);
  const clubName = hasSave ? (rosterMeta.clubName ?? "").trim() : "";
  const isEmptyRoster = clubPlayerCount() === 0;

  // Empty club has no tab chrome — reset to First Team so Mentoring pane
  // markup cannot linger in the empty container.
  if (isEmptyRoster && squadViewMode !== "firstTeam") {
    squadUnitView = "personalities";
    setSquadViewMode("firstTeam");
    return;
  }

  rosterTablePanelEl.classList.toggle("is-empty-roster", isEmptyRoster);
  rosterUploadBtnEl.classList.toggle("is-cta", isEmptyRoster);
  squadViewToolbarStartEl.hidden = isEmptyRoster;
  rosterClubLineEl.hidden = isEmptyRoster;
  squadViewTabsEl.hidden = isEmptyRoster;
  // Empty copy lives on the upload “+” tooltip instead of the grid.
  rosterEmptyEl.hidden = true;
  if (isSquadUnitMode(squadViewMode) && squadUnitView === "personalities") {
    squadPersonalitiesPaneEl.hidden = false;
    squadMentoringPaneEl.hidden = true;
    squadEvolutionEl.hidden = true;
  }

  if (clubName) {
    rosterClubLineEl.textContent = clubName;
    rosterClubLineEl.classList.remove("is-empty");
    rosterClubLineEl.title = clubName;
  } else {
    rosterClubLineEl.textContent = "—";
    rosterClubLineEl.classList.add("is-empty");
    rosterClubLineEl.removeAttribute("title");
  }

  const tipParts: string[] = [];
  if (hasSave && rosterMeta.saveName) {
    tipParts.push(rosterMeta.saveName);
  } else if (!useRosterApi) {
    tipParts.push(
      "Live extract needs npm run dev. Stored Career Saves still load from localStorage.",
    );
  }
  if (tipParts.length > 0) {
    rosterSaveControllerEl.title = tipParts.join("\n");
    rosterSaveControllerEl.setAttribute("aria-label", tipParts.join(". "));
  } else {
    rosterSaveControllerEl.removeAttribute("title");
    rosterSaveControllerEl.setAttribute("aria-label", "Career Save");
  }

  const saveCount = listRosterSaveNames(rosterStore).length;
  const emptyUploadTip =
    "Load a Career Save to rank First Team, Reserves, and Under 19s by personality HAS.";
  const loadLabel = rosterAmendTarget
    ? "Overwrite selected save"
    : isEmptyRoster
      ? emptyUploadTip
      : "Load Career Save";
  rosterUploadBtnEl.title = loadLabel;
  rosterUploadBtnEl.setAttribute("aria-label", loadLabel);
  const savesLabel = `Manage saves (${saveCount})`;
  rosterSavesBtnEl.title = savesLabel;
  rosterSavesBtnEl.setAttribute("aria-label", savesLabel);

  const unitPlayers = rosterPlayers;

  rosterStatusEl.classList.toggle("is-error", Boolean(rosterMeta.error));
  // Don't clobber live settle/extract progress while a refresh is in flight,
  // or a just-finished Updated flash from showRosterUpdatedStatus.
  if (!rosterRefreshInFlight && !rosterStatusEl.classList.contains("is-success")) {
    applyRosterTrustStatus();
  }

  type RankedSquadPlayer = {
    player: RosterPlayer;
    score: number | null;
  };
  const ranked: RankedSquadPlayer[] = rankPlayersForPersonalityGrid(unitPlayers);
  const atClub = ranked.filter(
    (entry) => entry.player.loan?.status !== "loanedOut",
  );

  for (const entry of atClub) {
    rosterBodyEl.append(createSquadPersonalityCard(entry.player, entry.score));
  }
}

function rankPlayersForPersonalityGrid(
  players: readonly RosterPlayer[],
): Array<{ player: RosterPlayer; score: number | null }> {
  const ranked = players.map((player) => {
    if (!playerExtractTrust(player).attrsEnough) {
      return { player, score: null as number | null };
    }
    const playerPa = rosterPersonalitySignals(player);
    if (!playerPa) return { player, score: null as number | null };
    const built = estimatesFromPersonalitySignals(playerPa);
    if (!built) return { player, score: null };
    const ha = hiddenQualityScore(built.estimates, built.visible);
    return {
      player,
      score: Number.isFinite(ha) ? ha : null,
    };
  });
  ranked.sort((a, b) => {
    const as = a.score;
    const bs = b.score;
    if (as == null && bs == null) {
      return (a.player.name || "").localeCompare(b.player.name || "", undefined, {
        sensitivity: "base",
      });
    }
    if (as == null) return 1;
    if (bs == null) return -1;
    if (bs !== as) return bs - as;
    return (a.player.name || "").localeCompare(b.player.name || "", undefined, {
      sensitivity: "base",
    });
  });
  return ranked;
}

/** Club-wide Out on loan tab (T005) — loanedOut only, FT → Reserves → U19. */
function renderLoansPage() {
  const byUnit = loansByUnit({
    firstTeam: firstTeamPlayers,
    reserves: reservesPlayers,
    under19s: under19sPlayers,
  });
  const units = ["firstTeam", "reserves", "under19s"] as const;
  let any = false;
  for (const unit of units) {
    const section = squadLoansPaneEl.querySelector<HTMLElement>(
      `.squad-loans-section[data-loans-unit="${unit}"]`,
    );
    const grid = squadLoansPaneEl.querySelector<HTMLElement>(
      `[data-loans-grid="${unit}"]`,
    );
    if (!section || !grid) continue;
    const players = byUnit[unit];
    grid.replaceChildren();
    if (players.length === 0) {
      section.hidden = true;
      continue;
    }
    any = true;
    section.hidden = false;
    for (const entry of rankPlayersForPersonalityGrid(players)) {
      grid.append(createSquadPersonalityCard(entry.player, entry.score));
    }
  }
  squadLoansEmptyEl.hidden = any;
}

type FirstTeamApiPlayer = LegacyRosterPlayer;

type FirstTeamApiResult = {
  type?: string;
  saveName: string;
  savePath?: string;
  teamId?: number;
  clubId?: number;
  clubName?: string | null;
  clubNameShort?: string | null;
  gameDate?: string | null;
  listAbs?: number;
  countHeader?: number;
  players?: FirstTeamApiPlayer[];
  hitCount?: number;
  elapsedMs: number;
  error?: string;
  favouredClub?: StoredFavouredClub | null;
  reserves?: (Omit<StoredReservesSquad, "players"> & {
    players?: FirstTeamApiPlayer[];
  }) | null;
  u19?: (Omit<StoredU19Squad, "players"> & {
    players?: FirstTeamApiPlayer[];
  }) | null;
};

type ProgressEvent = {
  type?: string;
  elapsedMs?: number;
  phase?: string;
  message?: string;
  pct?: number;
  etaMs?: number | null;
  outBytes?: number;
  extract?: string;
};

type SaveDiskStat = {
  saveName: string;
  path: string;
  mtimeMs: number;
  size: number;
};

function saveNamesMatch(a: string, b: string): boolean {
  return a.localeCompare(b, undefined, { sensitivity: "accent" }) === 0;
}

function rosterSaveDiskLinked(saveName: string): boolean {
  if (!useRosterApi) return false;
  const entry = rosterStore.saves[saveName];
  return Boolean(entry?.diskPath);
}

async function fetchSaveDiskStat(saveName: string): Promise<SaveDiskStat | null> {
  if (!useRosterApi) return null;
  try {
    const res = await fetch(
      `/api/roster/save-stat?save=${encodeURIComponent(saveName)}`,
    );
    if (!res.ok) return null;
    return (await res.json()) as SaveDiskStat;
  } catch {
    return null;
  }
}

/**
 * Bind a store slot to its on-disk path only.
 * Never stamp `diskMtimeMs` here — that field means "mtime at last successful
 * extract". Bind-alone stamps hid newer FM saves and skipped auto-sync (T010).
 */
function patchRosterDiskPath(saveName: string, stat: SaveDiskStat): void {
  const entry = rosterStore.saves[saveName];
  if (!entry) return;
  if (entry.diskPath === stat.path) return;
  rosterStore = upsertRoster(rosterStore, {
    ...entry,
    diskPath: stat.path,
    diskMtimeMs: entry.diskMtimeMs ?? null,
  });
}

async function tryBindSaveToDisk(saveName: string): Promise<boolean> {
  const stat = await fetchSaveDiskStat(saveName);
  if (!stat) return false;
  patchRosterDiskPath(saveName, stat);
  return true;
}

async function bindAllSavesToDisk(): Promise<void> {
  for (const name of listRosterSaveNames(rosterStore)) {
    if (!rosterStore.saves[name]?.diskPath) {
      await tryBindSaveToDisk(name);
    }
  }
}

function formatProgress(p: ProgressEvent): string {
  const parts: string[] = [];
  if (p.pct != null) parts.push(`${p.pct}%`);
  if (p.extract === "favoured-club" && !p.message?.toLowerCase().includes("favour")) {
    parts.push("Favoured club");
  }
  if (p.message) parts.push(p.message);
  else if (p.phase) parts.push(p.phase);
  if (p.elapsedMs != null) parts.push(`${(p.elapsedMs / 1000).toFixed(1)}s`);
  if (p.etaMs != null && p.etaMs > 0) {
    parts.push(`~${(p.etaMs / 1000).toFixed(0)}s left`);
  }
  if (p.outBytes) parts.push(`${(p.outBytes / 1e6).toFixed(0)}MB out`);
  return parts.join(" · ");
}

/** Live extract/settle feedback in the save-controller status strip. */
function setRosterLiveStatus(text: string, detail?: string) {
  if (rosterStatusClearTimer) {
    clearTimeout(rosterStatusClearTimer);
    rosterStatusClearTimer = null;
  }
  rosterStatusEl.classList.remove("is-error", "is-success");
  rosterStatusEl.textContent = text;
  const tip = (detail ?? text).trim();
  if (tip) {
    rosterStatusEl.title = tip;
    rosterStatusEl.setAttribute("aria-label", tip);
  } else {
    rosterStatusEl.removeAttribute("title");
    rosterStatusEl.removeAttribute("aria-label");
  }
}

/** Compact in-strip label; full process detail lives in the hover tooltip. */
function setRosterSyncStatus(detail: string) {
  setRosterLiveStatus("Syncing", detail);
}

function setRosterSyncing(syncing: boolean) {
  rosterSaveControllerEl.classList.toggle("is-syncing", syncing);
}

function notifyRosterRefreshIdle() {
  const waiters = rosterRefreshIdleWaiters;
  rosterRefreshIdleWaiters = [];
  for (const resolve of waiters) resolve();
}

function whenRosterRefreshIdle(): Promise<void> {
  if (!rosterRefreshInFlight) return Promise.resolve();
  return new Promise((resolve) => {
    rosterRefreshIdleWaiters.push(resolve);
  });
}

function flashRosterSoftUpdate() {
  rosterTablePanelEl.classList.remove("is-soft-updated");
  // Restart CSS animation.
  void rosterTablePanelEl.offsetWidth;
  rosterTablePanelEl.classList.add("is-soft-updated");
  window.setTimeout(() => {
    rosterTablePanelEl.classList.remove("is-soft-updated");
  }, 1200);
}

function clubExtractTrustSummary() {
  return summarizeExtractTrust(clubAllPlayers());
}

function applyRosterTrustStatus() {
  let statusText = "";
  let title: string | null = null;
  if (rosterMeta.error) {
    statusText = rosterMeta.error;
    title = rosterMeta.error;
  } else if (rosterAmendTarget) {
    statusText = "Ready to overwrite";
    title = `Next upload overwrites ${rosterAmendTarget}`;
  } else if (rosterMeta.source === "save" && clubPlayerCount() > 0) {
    statusText = formatExtractTrustStatus(clubExtractTrustSummary());
    title = statusText || null;
  }
  rosterStatusEl.textContent = statusText;
  if (title) {
    rosterStatusEl.title = title;
    rosterStatusEl.setAttribute("aria-label", title);
  } else {
    rosterStatusEl.removeAttribute("title");
    rosterStatusEl.removeAttribute("aria-label");
  }
}

function showRosterUpdatedStatus(body: FirstTeamApiResult) {
  const dateBit = body.gameDate ? ` · ${body.gameDate}` : "";
  const count = body.players?.length ?? 0;
  const trust = formatExtractTrustStatus(clubExtractTrustSummary());
  const flash = `Updated${dateBit} · ${count} players`;
  setRosterLiveStatus(flash, trust ? `${flash}\n${trust}` : flash);
  rosterStatusEl.classList.add("is-success");
  rosterStatusClearTimer = setTimeout(() => {
    rosterStatusClearTimer = null;
    if (rosterRefreshInFlight) return;
    rosterStatusEl.classList.remove("is-success");
    applyRosterTrustStatus();
  }, 5000);
}

async function consumeExtractStream(
  res: Response,
  onProgress: (p: ProgressEvent) => void,
): Promise<FirstTeamApiResult> {
  if (!res.body) {
    const body = (await res.json()) as FirstTeamApiResult;
    if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`);
    return body;
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  let result: FirstTeamApiResult | null = null;
  let errorMsg: string | null = null;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      let obj: Record<string, unknown>;
      try {
        obj = JSON.parse(trimmed) as Record<string, unknown>;
      } catch {
        continue;
      }
      if (obj.type === "progress") {
        onProgress(obj as ProgressEvent);
      } else if (obj.type === "result") {
        result = obj as unknown as FirstTeamApiResult;
      } else if (obj.type === "error") {
        errorMsg = String(obj.error ?? "Extract failed");
      }
    }
  }
  if (errorMsg) throw new Error(errorMsg);
  if (!result) throw new Error("Extract stream ended without a result");
  return result;
}

function setRosterControlsDisabled(disabled: boolean) {
  rosterSaveControllerEl.classList.toggle("is-busy", disabled);
  rosterTablePanelEl.classList.toggle("is-busy", disabled);
  rosterUploadEl.disabled = disabled;
  rosterUploadBtnEl.disabled = disabled;
  rosterSavesBtnEl.disabled = disabled;
  for (const btn of rosterSavesListEl.querySelectorAll("button")) {
    btn.disabled = disabled;
  }
}

function clearRosterAmendTarget() {
  if (!rosterAmendTarget) return;
  rosterAmendTarget = null;
  renderRoster();
}

function dismissRosterFileDialog() {
  if (!rosterFileDialogOpen) return;
  rosterFileDialogOpen = false;
  clearRosterAmendTarget();
}

function openRosterFilePicker() {
  setRosterSavesMenuOpen(false);
  rosterFileDialogOpen = true;
  rosterUploadEl.click();
}

function mapApiSquadPlayers(
  players: FirstTeamApiPlayer[] | undefined,
): RosterPlayer[] {
  return (players ?? []).map((p) =>
    normalizeRosterPlayer({
      ...p,
      uid: p.uid ?? 0,
      name: p.name ?? "",
      kind: p.kind ?? "UNKNOWN",
      source: p.source ?? "save",
    }),
  );
}

function persistExtractResult(
  body: FirstTeamApiResult,
  diskBinding?: SaveDiskStat | null,
  options?: { soft?: boolean },
) {
  const players: RosterPlayer[] = mapApiSquadPlayers(body.players);
  const replaceName = rosterAmendTarget;
  const prev = rosterStore.saves[body.saveName];
  const favouredClub: StoredFavouredClub | null | undefined = body.favouredClub
    ? {
        clubId: body.favouredClub.clubId ?? body.clubId,
        clubName: body.favouredClub.clubName ?? body.clubName ?? null,
        clubNameShort:
          body.favouredClub.clubNameShort ?? body.clubNameShort ?? null,
        affinity: body.favouredClub.affinity ?? 100,
        hitCount: body.favouredClub.hitCount,
        anchoredCount: body.favouredClub.anchoredCount,
        elapsedMs: body.favouredClub.elapsedMs,
        error: body.favouredClub.error ?? null,
        players: (body.favouredClub.players ?? []).map((p) => ({
          uid: Number(p.uid),
          name: p.name ?? null,
          affinity: Number(p.affinity) || 100,
          ca: p.ca != null ? Number(p.ca) : null,
          pa: p.pa != null ? Number(p.pa) : null,
        })),
      }
    : body.favouredClub === null
      ? null
      : undefined;
  const reserves: StoredReservesSquad | null | undefined =
    body.reserves != null
      ? {
          iiName: body.reserves.iiName,
          clubId: body.reserves.clubId,
          teamId: body.reserves.teamId ?? null,
          countHeader: body.reserves.countHeader,
          capaResolved: body.reserves.capaResolved,
          // Tip-only history — full CA strips for II/U19 blow localStorage and
          // used to leave soft-sync on stale slim rows (names, no personality).
          players: mapApiSquadPlayers(body.reserves.players).map(
            tipOnlyAttributeHistory,
          ),
        }
      : body.reserves === null
        ? null
        : undefined;
  const u19: StoredU19Squad | null | undefined =
    body.u19 != null
      ? {
          u19Name: body.u19.u19Name,
          countHeader: body.u19.countHeader,
          capaResolved: body.u19.capaResolved,
          players: mapApiSquadPlayers(body.u19.players).map(
            tipOnlyAttributeHistory,
          ),
        }
      : body.u19 === null
        ? null
        : undefined;
  rosterStore = upsertRoster(rosterStore, {
    saveName: body.saveName,
    clubId: body.clubId,
    teamId: body.teamId,
    clubName: body.clubName ?? undefined,
    clubNameShort: body.clubNameShort ?? undefined,
    gameDate: body.gameDate ?? null,
    elapsedMs: body.elapsedMs,
    extractedAt: new Date().toISOString(),
    players,
    diskPath:
      diskBinding?.path ??
      body.savePath ??
      prev?.diskPath ??
      null,
    diskMtimeMs:
      diskBinding?.mtimeMs ?? prev?.diskMtimeMs ?? null,
    ...(favouredClub !== undefined ? { favouredClub } : {}),
    ...(reserves !== undefined ? { reserves } : {}),
    ...(u19 !== undefined ? { u19 } : {}),
  });
  haHistoryStore = mergeHaHistoryFromRoster(
    haHistoryStore,
    rosterStore.saves[body.saveName]!,
  );
  if (replaceName && replaceName !== body.saveName) {
    rosterStore = deleteRoster(rosterStore, replaceName);
    rosterStore = setActiveRoster(rosterStore, body.saveName);
  }
  if (!options?.soft) rosterAmendTarget = null;
  // Apply the in-memory upsert directly — reloading LS here can resurrect a
  // pre-persist snapshot if another tab/HMR raced the write (T010).
  applyActiveRosterFromStore({
    soft: Boolean(options?.soft),
    reload: false,
  });
}

/** FM writes after Save click — wait until size/mtime stop changing before extract. */
const SAVE_SETTLE_POLL_MS = 2000;
const SAVE_SETTLE_STABLE_MS = 15_000;
const SAVE_SETTLE_MAX_MS = 180_000;

function sleepMs(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForSaveDiskStable(
  saveName: string,
  onWaiting?: (info: {
    stat: SaveDiskStat;
    elapsedMs: number;
    stableForMs: number;
  }) => void,
): Promise<SaveDiskStat | null> {
  const started = Date.now();
  let last: SaveDiskStat | null = null;
  let stableSince = 0;

  while (Date.now() - started < SAVE_SETTLE_MAX_MS) {
    const stat = await fetchSaveDiskStat(saveName);
    if (!stat) return last;
    const now = Date.now();
    if (
      last &&
      stat.mtimeMs === last.mtimeMs &&
      stat.size === last.size
    ) {
      const stableForMs = now - stableSince;
      onWaiting?.({
        stat,
        elapsedMs: now - started,
        stableForMs,
      });
      if (stableForMs >= SAVE_SETTLE_STABLE_MS) return stat;
    } else {
      last = stat;
      stableSince = now;
      onWaiting?.({
        stat,
        elapsedMs: now - started,
        stableForMs: 0,
      });
    }
    await sleepMs(SAVE_SETTLE_POLL_MS);
  }
  return last;
}

function formatSaveSettleStatus(info: {
  elapsedMs: number;
  stableForMs: number;
  stat: SaveDiskStat;
}): string {
  const elapsedSec = Math.max(1, Math.round(info.elapsedMs / 1000));
  const sizeMb = (info.stat.size / 1e6).toFixed(0);
  if (info.stableForMs <= 0) {
    return `Waiting for write… ${elapsedSec}s · ${sizeMb}MB`;
  }
  const needSec = Math.ceil(SAVE_SETTLE_STABLE_MS / 1000);
  const haveSec = Math.min(
    needSec,
    Math.floor(info.stableForMs / 1000),
  );
  return `Settling ${haveSec}/${needSec}s · ${sizeMb}MB`;
}

async function refreshSaveFromDisk(
  saveName: string,
  options?: {
    replaceName?: string | null;
    /** Wait for FM to finish writing before extracting (auto-sync / poll). */
    waitForSettle?: boolean;
    reason?: string;
    /**
     * Non-blocking auto-sync: keep the UI usable, show progress in the status
     * strip, then soft-apply when the extract finishes.
     */
    background?: boolean;
  },
): Promise<boolean> {
  if (!useRosterApi) return false;
  if (rosterRefreshInFlight) {
    if (options?.background) rosterBackgroundSyncQueued = true;
    return false;
  }

  let stat = await fetchSaveDiskStat(saveName);
  if (!stat) return false;

  const background = Boolean(options?.background);
  let ok = false;
  let updatedBody: FirstTeamApiResult | null = null;
  let backgroundError: string | null = null;

  rosterRefreshInFlight = true;
  rosterBackgroundSync = background;
  if (!background) {
    rosterAmendTarget = options?.replaceName ?? saveName;
    setRosterControlsDisabled(true);
  } else {
    setRosterSyncing(true);
  }

  try {
    if (options?.waitForSettle) {
      if (background) {
        setRosterSyncStatus(`${stat.saveName}\nWaiting for write…`);
      } else {
        setRosterLiveStatus("Waiting for write…", stat.saveName);
      }
      const settled = await waitForSaveDiskStable(stat.saveName, (info) => {
        const detail = `${info.stat.saveName}\n${formatSaveSettleStatus(info)}`;
        if (background) setRosterSyncStatus(detail);
        else setRosterLiveStatus(formatSaveSettleStatus(info), detail);
      });
      if (!settled) {
        if (!background) rosterAmendTarget = null;
        backgroundError = background
          ? "Could not confirm save finished writing"
          : null;
        return false;
      }
      stat = settled;
    }

    if (background) {
      setRosterSyncStatus(`${stat.saveName}\nReading from disk…`);
    } else {
      setRosterLiveStatus("Reading from disk…", stat.saveName);
    }
    const res = await fetch(
      `/api/roster/first-team?save=${encodeURIComponent(stat.saveName)}`,
    );
    const body = await consumeExtractStream(res, (p) => {
      const label = formatProgress(p);
      const detail = `${stat.saveName}\n${label}`;
      if (background) setRosterSyncStatus(detail);
      else setRosterLiveStatus(label, detail);
    });
    body.saveName = stat.saveName;
    const fresh = await fetchSaveDiskStat(stat.saveName);
    // Foreground overwrite may rename the slot; background never touches amend.
    if (!background && options?.replaceName) {
      rosterAmendTarget = options.replaceName;
    }
    persistExtractResult(body, fresh ?? stat, { soft: background });
    rosterMeta = { ...rosterMeta, error: undefined };
    updatedBody = body;
    ok = true;
    return true;
  } catch (err) {
    const raw = err instanceof Error ? err.message : String(err);
    if (background) {
      backgroundError = raw;
    } else {
      rosterMeta = {
        ...rosterMeta,
        error: raw,
      };
      rosterAmendTarget = null;
    }
    return false;
  } finally {
    rosterRefreshInFlight = false;
    rosterBackgroundSync = false;
    rosterUploadEl.value = "";
    if (!background) setRosterControlsDisabled(false);
    else setRosterSyncing(false);
    renderRoster();
    refreshActiveSquadSideView();
    if (ok && updatedBody) {
      if (background) flashRosterSoftUpdate();
      showRosterUpdatedStatus(updatedBody);
    } else if (background && backgroundError) {
      setRosterLiveStatus(`Background sync failed — ${backgroundError}`);
      rosterStatusEl.classList.add("is-error");
    } else if (background && !ok) {
      // Never leave the strip on Syncing after a quiet failure.
      if (rosterStatusEl.textContent === "Syncing") {
        setRosterLiveStatus("");
      }
    }
    notifyRosterRefreshIdle();
    if (background && rosterBackgroundSyncQueued) {
      rosterBackgroundSyncQueued = false;
      // Let any waiting manual upload/update claim the lock first.
      setTimeout(() => {
        if (rosterRefreshInFlight) {
          rosterBackgroundSyncQueued = true;
          return;
        }
        void maybeRefreshActiveSaveFromDisk({
          reason: "Save changed on disk",
          waitForSettle: true,
          background: true,
        });
      }, 0);
    }
  }
}

async function maybeRefreshActiveSaveFromDisk(options?: {
  reason?: string;
  /** When false, skip client settle (server already waited). Default true. */
  waitForSettle?: boolean;
  /** Default true — daily/auto saves should not lock the UI. */
  background?: boolean;
}): Promise<void> {
  const active = rosterStore.activeSaveName;
  if (!active) return;
  if (rosterRefreshInFlight) {
    if (options?.background !== false) rosterBackgroundSyncQueued = true;
    return;
  }
  const entry = rosterStore.saves[active];
  if (!entry) return;

  const stat = await fetchSaveDiskStat(active);
  if (!stat) return;

  const waitForSettle = options?.waitForSettle !== false;
  const background = options?.background !== false;

  // Path bind only — never stamp diskMtimeMs ahead of a successful extract.
  if (!entry.diskPath) {
    patchRosterDiskPath(active, stat);
  }

  const latest = rosterStore.saves[active] ?? entry;
  if (!shouldRefreshRosterFromDisk(latest, stat.mtimeMs)) return;

  await refreshSaveFromDisk(active, {
    replaceName: background ? null : active,
    waitForSettle,
    reason: options?.reason,
    background,
  });
}

function startSaveAutoSync(): void {
  if (!useRosterApi || saveAutoSyncStarted) return;
  saveAutoSyncStarted = true;

  void (async () => {
    await bindAllSavesToDisk();
    // Heal bind-only mtime stamps / catch FM writes while FMT was closed.
    await maybeRefreshActiveSaveFromDisk({
      reason: "Startup disk check",
      waitForSettle: false,
      background: true,
    });
  })();

  try {
    saveEventSource = new EventSource("/api/roster/events");
    saveEventSource.onmessage = (ev) => {
      let data: { type?: string; saveName?: string };
      try {
        data = JSON.parse(ev.data) as { type?: string; saveName?: string };
      } catch {
        return;
      }
      if (data.type !== "save-changed" || !data.saveName) return;
      const active = rosterStore.activeSaveName;
      if (!active || !saveNamesMatch(data.saveName, active)) return;
      // Server already debounced + waited for a stable write.
      void maybeRefreshActiveSaveFromDisk({
        reason: "Save changed on disk",
        waitForSettle: false,
        background: true,
      });
    };
  } catch {
    // SSE unavailable — poll fallback below
  }

  if (savePollTimer) clearInterval(savePollTimer);
  savePollTimer = setInterval(() => {
    void maybeRefreshActiveSaveFromDisk({ background: true });
  }, 8000);
}

async function uploadFirstTeamSave(file: File): Promise<void> {
  if (!useRosterApi) {
    rosterAmendTarget = null;
    rosterMeta = {
      ...rosterMeta,
      error: "Live extract only available under npm run dev",
    };
    renderRoster();
    return;
  }

  if (rosterRefreshInFlight) {
    setRosterLiveStatus(
      rosterBackgroundSync
        ? "Waiting for background sync to finish…"
        : "Waiting for current extract to finish…",
    );
    await whenRosterRefreshIdle();
  }

  const amending = Boolean(rosterAmendTarget);
  rosterRefreshInFlight = true;
  rosterBackgroundSync = false;
  setRosterControlsDisabled(true);
  setRosterLiveStatus(amending ? "Overwriting save…" : "Uploading…");
  rosterStatusEl.title = amending
    ? `${rosterAmendTarget} ← ${file.name}`
    : file.name;
  let updatedBody: FirstTeamApiResult | null = null;
  try {
    const res = await fetch("/api/roster/first-team", {
      method: "POST",
      headers: {
        "Content-Type": "application/octet-stream",
        "X-Fmt-Filename": encodeURIComponent(file.name),
      },
      body: file,
    });
    const body = await consumeExtractStream(res, (p) => {
      const label = formatProgress(p);
      setRosterLiveStatus(label);
      rosterStatusEl.title = `${file.name}\n${label}`;
    });
    body.saveName = file.name;
    const diskStat = await fetchSaveDiskStat(file.name);
    persistExtractResult(body, diskStat);
    if (!diskStat) void tryBindSaveToDisk(file.name);
    rosterMeta = { ...rosterMeta, error: undefined };
    updatedBody = body;
  } catch (err) {
    const raw = err instanceof Error ? err.message : String(err);
    const networkish =
      /networkerror|failed to fetch|load failed|network request failed/i.test(
        raw,
      );
    rosterMeta = {
      ...rosterMeta,
      error: networkish
        ? `${raw} — usually the Vite dev server restarted or dropped the connection mid-upload. Keep npm run dev running, hard-refresh, and retry.`
        : raw,
    };
    rosterAmendTarget = null;
  } finally {
    rosterRefreshInFlight = false;
    rosterBackgroundSync = false;
    rosterUploadEl.value = "";
    setRosterControlsDisabled(false);
    renderRoster();
    refreshActiveSquadSideView();
    if (updatedBody) showRosterUpdatedStatus(updatedBody);
    notifyRosterRefreshIdle();
  }
}

rosterUploadBtnEl.addEventListener("click", () => {
  openRosterFilePicker();
});

rosterUploadEl.addEventListener("change", () => {
  rosterFileDialogOpen = false;
  const file = rosterUploadEl.files?.[0];
  if (file) {
    void uploadFirstTeamSave(file);
    return;
  }
  clearRosterAmendTarget();
});

rosterUploadEl.addEventListener("cancel", () => {
  dismissRosterFileDialog();
});

// Browsers without input `cancel`: clear overwrite intent when the dialog is dismissed.
window.addEventListener("focus", () => {
  if (!rosterFileDialogOpen) return;
  window.setTimeout(() => {
    if (!rosterFileDialogOpen) return;
    if (rosterUploadEl.files?.length) {
      rosterFileDialogOpen = false;
      return;
    }
    dismissRosterFileDialog();
  }, 300);
});

rosterSavesBtnEl.addEventListener("click", (e) => {
  e.stopPropagation();
  setRosterSavesMenuOpen(!rosterSavesMenuOpen);
});

rosterSavesMenuEl.addEventListener("click", (e) => {
  e.stopPropagation();
  const btn = (e.target as HTMLElement).closest<HTMLButtonElement>(
    "button[data-action]",
  );
  if (!btn?.dataset.saveName || !btn.dataset.action) return;
  const name = btn.dataset.saveName;
  const action = btn.dataset.action;

  if (action === "select") {
    rosterStore = setActiveRoster(rosterStore, name);
    applyActiveRosterFromStore();
    setRosterSavesMenuOpen(false);
    renderRoster();
    refreshActiveSquadSideView();
    return;
  }

  if (action === "update") {
    rosterStore = setActiveRoster(rosterStore, name);
    applyActiveRosterFromStore();
    renderRoster();
    refreshActiveSquadSideView();
    setRosterSavesMenuOpen(false);
    void (async () => {
      if (rosterRefreshInFlight) {
        setRosterLiveStatus(
          rosterBackgroundSync
            ? "Waiting for background sync to finish…"
            : "Waiting for current extract to finish…",
        );
        await whenRosterRefreshIdle();
      }
      const ok = await refreshSaveFromDisk(name, {
        replaceName: name,
        background: false,
      });
      if (!ok) {
        rosterAmendTarget = name;
        renderRoster();
        openRosterFilePicker();
      }
    })();
    return;
  }

  if (action === "delete") {
    if (!confirm(`Delete Career Save extract “${name}”?`)) return;
    if (rosterAmendTarget === name) rosterAmendTarget = null;
    rosterStore = deleteRoster(rosterStore, name);
    applyActiveRosterFromStore();
    renderRoster();
    refreshActiveSquadSideView();
  }
});

document.addEventListener("click", () => {
  if (rosterSavesMenuOpen) setRosterSavesMenuOpen(false);
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && rosterSavesMenuOpen) {
    setRosterSavesMenuOpen(false);
  }
});

function rosterSaveCount(): number {
  return listRosterSaveNames(rosterStore).length;
}

function candidateFromRosterPlayer(
  player: RosterPlayer,
): MentoringCandidate | null {
  if (!isMentoringCompleteEnough(player)) return null;
  const pa = rosterPersonalitySignals(player);
  if (!pa) return null;
  const resolvedName = rosterResolvedName(player);
  if (!resolvedName) return null;

  const exact = (key: keyof PersonalitySignals): number | undefined => {
    const raw = pa[key];
    return raw != null && Number.isFinite(raw) ? raw : undefined;
  };

  const ageRaw = rosterPlayerAge(player, rosterMeta.gameDate);
  const age = ageRaw != null ? ageRaw : undefined;

  const built = estimatesFromPersonalitySignals(pa);
  const combo = matchPersonalityComboFromAttrs(pa, {
    isRegen: player.kind === "NEWGEN",
    ...(age !== undefined ? { age } : {}),
  });
  const haScore = built
    ? hiddenQualityScore(built.estimates, built.visible)
    : combo?.haScore;

  const bands: NonNullable<MentoringSubject["bands"]> = {};
  for (const trait of [
    "determination",
    "professionalism",
    "ambition",
    "loyalty",
    "sportsmanship",
    "controversy",
    "pressure",
    "temperament",
  ] as const) {
    const value = exact(trait);
    if (value === undefined) continue;
    bands[trait] = { min: value, max: value, midpoint: value };
  }

  return {
    id: String(player.uid),
    name: resolvedName,
    ...(age !== undefined ? { age } : {}),
    ...(exact("determination") !== undefined
      ? { determination: exact("determination") }
      : {}),
    ...(exact("leadership") !== undefined
      ? { leadership: exact("leadership") }
      : {}),
    ...(exact("professionalism") !== undefined
      ? { professionalism: exact("professionalism") }
      : {}),
    ...(exact("ambition") !== undefined ? { ambition: exact("ambition") } : {}),
    ...(exact("loyalty") !== undefined ? { loyalty: exact("loyalty") } : {}),
    ...(exact("sportsmanship") !== undefined
      ? { sportsmanship: exact("sportsmanship") }
      : {}),
    ...(exact("controversy") !== undefined
      ? { controversy: exact("controversy") }
      : {}),
    ...(exact("pressure") !== undefined ? { pressure: exact("pressure") } : {}),
    ...(exact("temperament") !== undefined
      ? { temperament: exact("temperament") }
      : {}),
    ...(haScore !== undefined && Number.isFinite(haScore) ? { haScore } : {}),
    ...(combo?.personality ? { personality: combo.personality } : {}),
    ...(combo?.mediaHandling ? { mediaHandling: combo.mediaHandling } : {}),
    ...(player.kind === "NEWGEN"
      ? { isRegen: true }
      : player.kind === "REAL"
        ? { isRegen: false }
        : {}),
    ...(Object.keys(bands).length ? { bands } : {}),
  };
}

function formatMentoringPlayerMeta(player: MentoringCandidate): string {
  const parts: string[] = [];
  if (player.age !== undefined) parts.push(`${player.age}y`);
  if (player.personality) parts.push(player.personality);
  if (player.mediaHandling) parts.push(player.mediaHandling);
  return parts.join(" · ");
}

/** Last whitespace token — table label; full name stays in the tooltip. */
function mentoringLastName(fullName: string): string {
  const trimmed = fullName.trim();
  if (!trimmed) return "—";
  const parts = trimmed.split(/\s+/);
  return parts[parts.length - 1] || trimmed;
}

function mentoringPlayerTooltip(
  player: MentoringCandidate,
  role: MentoringInfluenceSeat,
): string {
  const seat =
    role === "high" ? "High" : role === "mid" ? "Mid" : "Low";
  const bits = [`${seat} influence`, player.name];
  const meta = formatMentoringPlayerMeta(player);
  if (meta) bits.push(meta);
  return bits.join(" · ");
}

function mentoringTraitValue(
  player: MentoringCandidate,
  trait: (typeof MENTORING_DISPLAY_ORDER)[number],
): number | undefined {
  const band = player.bands?.[trait];
  if (band && Number.isFinite(band.midpoint)) return band.midpoint;
  const raw = player[trait];
  return typeof raw === "number" && Number.isFinite(raw) ? raw : undefined;
}

function createMentoringPlayerHeader(
  player: MentoringCandidate,
  role: MentoringInfluenceSeat,
): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "mentoring-col-head";

  const name = document.createElement("span");
  name.className = "mentoring-col-name";
  name.textContent = mentoringLastName(player.name);
  name.title = mentoringPlayerTooltip(player, role);

  wrap.append(name);
  return wrap;
}

type MentoringDeltaMark =
  | { kind: "plus"; values: number[]; labels: string[] }
  | { kind: "arrow"; dir: "up" | "down"; good: boolean };

/** Signed “mentor better than mentee” amount (controversy inverted). */
function mentoringMentorEdge(
  trait: (typeof MENTORING_DISPLAY_ORDER)[number],
  mentorValue: number,
  menteeValue: number,
): number {
  return trait === "controversy"
    ? menteeValue - mentorValue
    : mentorValue - menteeValue;
}

function createMentoringComparePair(
  value: number | undefined,
  trait: (typeof MENTORING_DISPLAY_ORDER)[number],
  mark?: MentoringDeltaMark,
): HTMLElement {
  const pair = document.createElement("span");
  pair.className = "compare-pair";

  const valEl = document.createElement("span");
  const deltaEl = document.createElement("span");
  deltaEl.className = "compare-delta is-empty";
  deltaEl.setAttribute("aria-hidden", "true");

  if (value === undefined || !Number.isFinite(value)) {
    valEl.className = "compare-val fmt-mid is-empty";
    valEl.textContent = "—";
    pair.append(valEl, deltaEl);
    return pair;
  }

  const tone = attributeTone(trait, value);
  valEl.textContent = formatMidCell(value);
  valEl.className = [
    "compare-val",
    "fmt-mid",
    tone === "good" ? "good" : "",
    tone === "bad" ? "bad" : "",
  ]
    .filter(Boolean)
    .join(" ");

  if (mark?.kind === "plus") {
    const shown = mark.values
      .map((value, index) => ({ value, label: mark.labels[index] ?? "" }))
      .filter((row) => Math.abs(row.value) >= 0.05);
    if (shown.length > 0) {
      deltaEl.replaceChildren();
      deltaEl.className = "compare-delta mentoring-delta-stack";
      deltaEl.removeAttribute("aria-hidden");
      shown.forEach((row, index) => {
        const chip = document.createElement("span");
        chip.className = row.value > 0 ? "is-up" : "is-down";
        chip.textContent = formatClimbDelta(row.value);
        if (row.label) chip.title = `${formatClimbDelta(row.value)} vs ${row.label}`;
        deltaEl.append(chip);
        if (index < shown.length - 1) {
          deltaEl.append(document.createTextNode(" "));
        }
      });
      deltaEl.title = shown
        .map((row) =>
          row.label
            ? `${formatClimbDelta(row.value)} vs ${row.label}`
            : formatClimbDelta(row.value),
        )
        .join(" · ");
    }
  } else if (mark?.kind === "arrow") {
    deltaEl.textContent = mark.dir === "up" ? "▲" : "▼";
    deltaEl.className = [
      "compare-delta",
      "mentoring-delta-arrow",
      mark.good ? "is-up" : "is-down",
    ].join(" ");
    deltaEl.removeAttribute("aria-hidden");
    deltaEl.title =
      mark.dir === "up"
        ? mark.good
          ? "Mentors higher — pulls up"
          : "Mentors higher — pulls the wrong way"
        : mark.good
          ? "Mentors lower — improves Controversy"
          : "Mentors lower — pulls down";
  }

  pair.append(valEl, deltaEl);
  return pair;
}

function createMentoringGroupTable(
  influencers: MentoringCandidate[],
  receivers: MentoringCandidate[],
  highlightPlayerId?: string,
): HTMLTableElement {
  const columns: { player: MentoringCandidate; role: MentoringInfluenceSeat }[] =
    [
      ...influencers.map((player, index) => ({
        player,
        role: (index === 0 ? "high" : "mid") as MentoringInfluenceSeat,
      })),
      ...receivers.map((player) => ({
        player,
        role: "low" as const,
      })),
    ];
  const highlightId =
    highlightPlayerId != null && highlightPlayerId !== ""
      ? String(highlightPlayerId)
      : null;

  const table = document.createElement("table");
  table.className = "mentoring-matrix fmt-table";

  const colgroup = document.createElement("colgroup");
  const attrCol = document.createElement("col");
  attrCol.className = "mentoring-col-attr";
  colgroup.append(attrCol);
  for (const _ of columns) {
    const col = document.createElement("col");
    col.className = "mentoring-col-player";
    colgroup.append(col);
  }
  table.append(colgroup);

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  const attrTh = document.createElement("th");
  attrTh.scope = "col";
  attrTh.textContent = "Attr";
  headRow.append(attrTh);
  for (const column of columns) {
    const th = document.createElement("th");
    th.scope = "col";
    th.className = "mentoring-player-col";
    th.dataset.playerId = String(column.player.id);
    if (column.role === "low") th.classList.add("is-mentee");
    if (highlightId && String(column.player.id) === highlightId) {
      th.classList.add("is-hover-col");
    }
    th.append(createMentoringPlayerHeader(column.player, column.role));
    headRow.append(th);
  }
  thead.append(headRow);
  table.append(thead);

  const tbody = document.createElement("tbody");
  for (const trait of MENTORING_DISPLAY_ORDER) {
    const tr = document.createElement("tr");
    tr.dataset.attribute = trait;

    const nameTd = document.createElement("td");
    const label =
      trait in ATTRIBUTE_LABELS
        ? ATTRIBUTE_LABELS[trait as keyof typeof ATTRIBUTE_LABELS]
        : trait === "determination"
          ? "Determination"
          : trait;
    const abbr =
      trait in PERSONALITY_ATTRIBUTE_ABBR
        ? PERSONALITY_ATTRIBUTE_ABBR[
            trait as keyof typeof PERSONALITY_ATTRIBUTE_ABBR
          ]
        : label.slice(0, 3);
    nameTd.innerHTML = `<span class="attr-name" title="${label}">${abbr}</span>`;
    tr.append(nameTd);

    const influencerValues = influencers
      .map((player) => mentoringTraitValue(player, trait))
      .filter((v): v is number => v !== undefined && Number.isFinite(v));
    const influencerTarget =
      influencerValues.length > 0
        ? influencerValues.reduce((sum, v) => sum + v, 0) /
          influencerValues.length
        : undefined;

    for (const column of columns) {
      const td = document.createElement("td");
      td.className = "mentoring-player-cell";
      td.dataset.playerId = String(column.player.id);
      if (column.role === "low") td.classList.add("is-mentee");
      if (highlightId && String(column.player.id) === highlightId) {
        td.classList.add("is-hover-col");
      }

      const value = mentoringTraitValue(column.player, trait);
      let mark: MentoringDeltaMark | undefined;

      if (column.role !== "low" && value !== undefined) {
        const paired = receivers.map((receiver) => {
          const receiverValue = mentoringTraitValue(receiver, trait);
          if (receiverValue === undefined) return null;
          return {
            value: mentoringMentorEdge(trait, value, receiverValue),
            label: mentoringLastName(receiver.name),
          };
        });
        const edges = paired.filter(
          (row): row is { value: number; label: string } => row !== null,
        );
        if (edges.some((row) => Math.abs(row.value) >= 0.05)) {
          mark = {
            kind: "plus",
            values: edges.map((row) => row.value),
            labels: edges.map((row) => row.label),
          };
        }
      } else if (
        column.role === "low" &&
        value !== undefined &&
        influencerTarget !== undefined
      ) {
        const diff = influencerTarget - value;
        if (Math.abs(diff) >= 0.05) {
          const influencersHigher = diff > 0;
          const good =
            trait === "controversy"
              ? !influencersHigher
              : influencersHigher;
          mark = {
            kind: "arrow",
            dir: influencersHigher ? "up" : "down",
            good,
          };
        }
      }

      td.append(createMentoringComparePair(value, trait, mark));
      tr.append(td);
    }
    tbody.append(tr);
  }
  table.append(tbody);
  return table;
}

/** ≥6 cards densify the 2-col grid enough to clip the Attr matrix body. */
const MENTORING_DENSE_GROUP_THRESHOLD = 6;

/** Full attr×player matrix on seat hover (optional click-pin for non-seat hosts). */
function wireMentoringMatrixTip(
  host: HTMLElement,
  buildTable: () => HTMLTableElement,
  opts?: { pinOnClick?: boolean },
): void {
  const pinOnClick = opts?.pinOnClick === true;
  ensureMentoringMatrixTipHoverBridge();

  const show = () => {
    clearMentoringMatrixTipHide();
    const tip = ensureMetricTip();
    tip.classList.remove("is-multiline");
    tip.classList.add("is-roster-attrs", "is-mentoring-matrix");
    const wrap = document.createElement("div");
    wrap.className = "mentoring-matrix-tip";
    wrap.append(buildTable());
    tip.replaceChildren(wrap);
    tip.hidden = false;
    // Force layout before measure — unhide can still report 0×0 synchronously.
    void tip.offsetWidth;
    positionMetricTip(host, tip);
    requestAnimationFrame(() => {
      if (!tip.hidden && tip.classList.contains("is-mentoring-matrix")) {
        positionMetricTip(host, tip);
      }
    });
  };

  host.addEventListener("mouseenter", show);
  host.addEventListener("mouseleave", scheduleMentoringMatrixTipHide);

  if (!pinOnClick) return;

  host.tabIndex = 0;
  host.setAttribute("role", "button");
  host.addEventListener("focus", show);
  host.addEventListener("blur", () => {
    if (metricTipEl?.dataset.pinned === "1") return;
    scheduleMentoringMatrixTipHide();
  });
  host.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    const tip = ensureMetricTip();
    if (
      !tip.hidden &&
      tip.dataset.pinned === "1" &&
      tip.classList.contains("is-mentoring-matrix")
    ) {
      hideMetricTip();
      return;
    }
    show();
    tip.dataset.pinned = "1";
  });
  host.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    host.click();
  });
}

/** Stable localStorage identity — survives re-extract, game-date, and logic-rev bumps. */
function mentoringPersistKey(): string {
  if (rosterMeta.source !== "save") return "";
  const name = (rosterMeta.saveName ?? rosterStore.activeSaveName ?? "").trim();
  return name;
}

/** In-memory session: rebuild candidates / suggestions when roster content or logic changes. */
function mentoringSessionKey(): string {
  const persist = mentoringPersistKey();
  const firstTeam = firstTeamMentoringPlayers();
  if (!persist || firstTeam.length === 0) return "";
  return [
    persist,
    rosterMeta.gameDate ?? "",
    // Fresh extract must bust Mentoring even when gameDate/count are unchanged
    // (name fixes, loan flips at same squad size) — T010.
    rosterMeta.extractedAt ?? "",
    String(firstTeam.length),
    String(MENTORING_LOGIC_REV),
  ].join("|");
}

function invalidateMentoringCache() {
  mentoringCache.generation += 1;
  mentoringCache = {
    persistKey: "",
    sessionKey: "",
    groups: [],
    dynamicsByPlayerId: {},
    candidates: null,
    suggestions: [],
    suggestionCursor: 0,
    suggestionsStatus: "idle",
    generation: mentoringCache.generation,
  };
  mentoringRenderFingerprint = "";
  mentoringPicker = null;
  mentoringDetailGroupId = null;
  mentoringDynamicsPlayerId = null;
  mentoringDynamicsGroupId = null;
  mentoringDynamicsDraft = null;
}

function emptyMentoringCache(
  persistKey: string,
  sessionKey: string,
  generation: number,
): MentoringCache {
  return {
    persistKey,
    sessionKey,
    groups: [],
    dynamicsByPlayerId: {},
    candidates: null,
    suggestions: [],
    suggestionCursor: 0,
    suggestionsStatus: "idle",
    generation,
  };
}

type MentoringStackPersist = Record<
  string,
  {
    groups: MentoringGroupRecord[];
    dynamicsByPlayerId?: Record<string, MentoringDynamicsLabel>;
  }
>;

function emptyMentoringDynamicsLabel(): MentoringDynamicsLabel {
  return {
    captaincy: null,
    hierarchy: null,
    socialGroup: null,
  };
}

function emptyMentoringDynamicsDraft(): MentoringDynamicsDraft {
  return {
    ...emptyMentoringDynamicsLabel(),
    influenceByPeerId: {},
  };
}

function mentoringInfluenceEdgeKey(fromId: string, toId: string): string {
  return `${fromId}>${toId}`;
}

function isMentoringEdgeLevel(value: unknown): value is MentoringInfluenceLevel {
  return (
    value === "none" ||
    value === "light" ||
    value === "average" ||
    value === "significant"
  );
}

function normalizeMentoringInfluenceEdges(
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

function normalizeMentoringDynamicsLabel(
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

function mentoringDynamicsCoreComplete(
  label: MentoringDynamicsLabel | null | undefined,
): boolean {
  return Boolean(
    label &&
      label.captaincy != null &&
      label.hierarchy != null &&
      label.socialGroup != null,
  );
}

function mentoringDynamicsCorePartial(
  label: MentoringDynamicsLabel | null | undefined,
): boolean {
  if (!label || mentoringDynamicsCoreComplete(label)) return false;
  return (
    label.captaincy != null ||
    label.hierarchy != null ||
    label.socialGroup != null
  );
}

function mentoringPeerInfluenceComplete(
  draft: MentoringPeerInfluenceDraft | null | undefined,
): boolean {
  return Boolean(draft && draft.on != null && draft.from != null);
}

function mentoringPeerInfluencePartial(
  draft: MentoringPeerInfluenceDraft | null | undefined,
): boolean {
  if (!draft || mentoringPeerInfluenceComplete(draft)) return false;
  return draft.on != null || draft.from != null;
}

function mentoringMemberInfluenceFromGroup(
  group: MentoringGroupRecord | null | undefined,
  playerId: string,
): Record<string, MentoringPeerInfluenceDraft> {
  const peers = (group?.memberIds ?? []).filter((id) => id !== playerId);
  const edges = group?.influenceEdges ?? {};
  const out: Record<string, MentoringPeerInfluenceDraft> = {};
  for (const peerId of peers) {
    out[peerId] = {
      on: edges[mentoringInfluenceEdgeKey(playerId, peerId)] ?? null,
      from: edges[mentoringInfluenceEdgeKey(peerId, playerId)] ?? null,
    };
  }
  return out;
}

function mentoringDynamicsIsComplete(
  label: MentoringDynamicsLabel | null | undefined,
  influenceByPeerId?: Record<string, MentoringPeerInfluenceDraft>,
): boolean {
  if (!mentoringDynamicsCoreComplete(label)) return false;
  if (!influenceByPeerId) return true;
  const peers = Object.values(influenceByPeerId);
  if (peers.length === 0) return true;
  return peers.every(mentoringPeerInfluenceComplete);
}

function mentoringDynamicsIsPartial(
  label: MentoringDynamicsLabel | null | undefined,
  influenceByPeerId?: Record<string, MentoringPeerInfluenceDraft>,
): boolean {
  if (mentoringDynamicsIsComplete(label, influenceByPeerId)) return false;
  if (mentoringDynamicsCorePartial(label) || mentoringDynamicsCoreComplete(label)) {
    return true;
  }
  if (!influenceByPeerId) return false;
  return Object.values(influenceByPeerId).some(
    (peer) => mentoringPeerInfluencePartial(peer) || mentoringPeerInfluenceComplete(peer),
  );
}

function mentoringDynamicsState(
  label: MentoringDynamicsLabel | null | undefined,
  influenceByPeerId?: Record<string, MentoringPeerInfluenceDraft>,
): "missing" | "partial" | "complete" {
  if (mentoringDynamicsIsComplete(label, influenceByPeerId)) return "complete";
  if (mentoringDynamicsIsPartial(label, influenceByPeerId)) return "partial";
  return "missing";
}

function getMentoringDynamicsLabel(playerId: string): MentoringDynamicsLabel {
  return (
    mentoringCache.dynamicsByPlayerId[playerId] ?? emptyMentoringDynamicsLabel()
  );
}

function mentoringMemberDynamicsState(
  playerId: string,
  group?: MentoringGroupRecord | null,
): "missing" | "partial" | "complete" {
  return mentoringDynamicsState(
    getMentoringDynamicsLabel(playerId),
    mentoringMemberInfluenceFromGroup(group, playerId),
  );
}

function mentoringHierarchyByIdMap(): Map<
  string,
  MentoringHierarchyLabel | null | undefined
> {
  const map = new Map<string, MentoringHierarchyLabel | null | undefined>();
  for (const [id, label] of Object.entries(mentoringCache.dynamicsByPlayerId)) {
    if (label.hierarchy != null) map.set(id, label.hierarchy);
  }
  return map;
}

function mentoringDynamicsSnapshotFromCandidate(
  player: MentoringCandidate,
): MentoringDynamicsSnapshot {
  return {
    ...(player.age !== undefined ? { age: player.age } : {}),
    ...(player.determination !== undefined
      ? { determination: player.determination }
      : {}),
    ...(player.leadership !== undefined ? { leadership: player.leadership } : {}),
    ...(player.haScore !== undefined ? { haScore: player.haScore } : {}),
    ...(player.personality ? { personality: player.personality } : {}),
  };
}

function normalizeMentoringGroupRecord(
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
  return {
    id: row.id,
    memberIds: row.memberIds.map(String),
    roles: row.roles,
    ...(edges ? { influenceEdges: edges } : {}),
  };
}

function loadMentoringStackFromStorage(persistKey: string): {
  groups: MentoringGroupRecord[];
  dynamicsByPlayerId: Record<string, MentoringDynamicsLabel>;
} {
  const empty = { groups: [] as MentoringGroupRecord[], dynamicsByPlayerId: {} };
  if (!persistKey) return empty;

  try {
    const raw =
      window.localStorage.getItem(MENTORING_STACK_STORAGE_KEY) ??
      window.localStorage.getItem(MENTORING_STACK_STORAGE_KEY_LEGACY);
    if (!raw) return empty;
    const store = JSON.parse(raw) as MentoringStackPersist;
    const direct = store[persistKey];
    if (direct && Array.isArray(direct.groups)) {
      const groups = direct.groups
        .map(normalizeMentoringGroupRecord)
        .filter((g): g is MentoringGroupRecord => g !== null);
      const dynamicsByPlayerId: Record<string, MentoringDynamicsLabel> = {};
      if (direct.dynamicsByPlayerId && typeof direct.dynamicsByPlayerId === "object") {
        for (const [id, value] of Object.entries(direct.dynamicsByPlayerId)) {
          const label = normalizeMentoringDynamicsLabel(value);
          if (label) dynamicsByPlayerId[id] = label;
        }
      }
      return { groups, dynamicsByPlayerId };
    }

    // Migrate legacy compound keys: `${saveName}|extractedAt|...|rev`
    const prefix = `${persistKey}|`;
    let best: {
      groups: MentoringGroupRecord[];
      dynamicsByPlayerId: Record<string, MentoringDynamicsLabel>;
    } | null = null;
    for (const [key, row] of Object.entries(store)) {
      if (!key.startsWith(prefix) || !row || !Array.isArray(row.groups)) continue;
      const groups = row.groups
        .map(normalizeMentoringGroupRecord)
        .filter((g): g is MentoringGroupRecord => g !== null);
      if (groups.length === 0) continue;
      const dynamicsByPlayerId: Record<string, MentoringDynamicsLabel> = {};
      if (row.dynamicsByPlayerId && typeof row.dynamicsByPlayerId === "object") {
        for (const [id, value] of Object.entries(row.dynamicsByPlayerId)) {
          const label = normalizeMentoringDynamicsLabel(value);
          if (label) dynamicsByPlayerId[id] = label;
        }
      }
      if (!best || groups.length > best.groups.length) {
        best = { groups, dynamicsByPlayerId };
      }
    }
    if (best) return best;
    return empty;
  } catch {
    return empty;
  }
}

function saveMentoringStackToStorage() {
  const persistKey = mentoringPersistKey() || mentoringCache.persistKey;
  if (!persistKey) return;
  try {
    const raw = window.localStorage.getItem(MENTORING_STACK_STORAGE_KEY);
    const store: MentoringStackPersist = raw ? JSON.parse(raw) : {};
    store[persistKey] = {
      groups: mentoringCache.groups,
      dynamicsByPlayerId: mentoringCache.dynamicsByPlayerId,
    };
    window.localStorage.setItem(MENTORING_STACK_STORAGE_KEY, JSON.stringify(store));
  } catch (err) {
    console.error("Failed to persist mentoring stack", err);
  }
}

function newMentoringGroupId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `mg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function mentoringMaxGroups(candidates: MentoringCandidate[]): number {
  return Math.floor(candidates.length / 3);
}

function mentoringAssignedPlayerIds(excludeGroupId?: string | null): Set<string> {
  const assigned = new Set<string>();
  for (const group of mentoringCache.groups) {
    if (excludeGroupId && group.id === excludeGroupId) continue;
    for (const id of group.memberIds) assigned.add(id);
  }
  return assigned;
}

function mentoringGroupIndex(groupId: string): number {
  return mentoringCache.groups.findIndex((group) => group.id === groupId);
}

function mentoringGroupLabel(index: number): string {
  return `Mentoring Group ${index + 1}`;
}

function mentoringGroupTableInfluencers(
  members: MentoringUnitMember[],
): MentoringCandidate[] {
  return ["high", "mid"]
    .map((seat) => members.find((member) => member.role === seat)?.player)
    .filter((player): player is MentoringCandidate => player !== undefined);
}

function mentoringGroupTableReceivers(
  members: MentoringUnitMember[],
): MentoringCandidate[] {
  return members
    .filter((member) => member.role === "low")
    .map((member) => member.player);
}

/** Keep directed edges whose endpoints remain in the trio. */
function mentoringEdgesForMembers(
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

function pruneMentoringGroups(_candidates: MentoringCandidate[]) {
  // Prune against full roster UIDs — not mentoring candidates. A player can
  // remain on the squad but fail candidate filters; wiping groups then would
  // permanently delete persisted mentoring units.
  // Also drop anyone tagged loanedOut — they cannot sit in an in-game group.
  const loanedOutIds = new Set<string>();
  for (const p of clubAllPlayers()) {
    if (p.uid == null || !Number.isFinite(p.uid)) continue;
    if (p.loan?.status === "loanedOut") loanedOutIds.add(String(p.uid));
  }
  const rosterIds = new Set(
    clubAllPlayers()
      .filter((p) => p.uid != null && Number.isFinite(p.uid))
      .map((p) => String(p.uid))
      .filter((id) => !loanedOutIds.has(id)),
  );
  if (rosterIds.size === 0) return;

  const seenPlayers = new Set<string>();
  const nextGroups: MentoringGroupRecord[] = [];

  for (const group of mentoringCache.groups) {
    const memberIds = group.memberIds.filter((id) => rosterIds.has(id));
    if (memberIds.length !== 3) continue;
    if (memberIds.some((id) => seenPlayers.has(id))) continue;
    for (const id of memberIds) seenPlayers.add(id);
    const influenceEdges = mentoringEdgesForMembers(
      group.influenceEdges,
      memberIds,
    );
    nextGroups.push({
      id: group.id,
      memberIds,
      roles: Object.fromEntries(
        Object.entries(group.roles).filter(([id]) => memberIds.includes(id)),
      ),
      ...(influenceEdges ? { influenceEdges } : {}),
    });
  }

  const changed =
    nextGroups.length !== mentoringCache.groups.length ||
    nextGroups.some((group, index) => {
      const prev = mentoringCache.groups[index];
      return (
        !prev ||
        prev.id !== group.id ||
        prev.memberIds.join("|") !== group.memberIds.join("|")
      );
    });

  mentoringCache.groups = nextGroups;
  if (
    mentoringDetailGroupId &&
    !nextGroups.some((group) => group.id === mentoringDetailGroupId)
  ) {
    mentoringDetailGroupId = null;
    if (mentoringDetailDialogEl.open) mentoringDetailDialogEl.close();
  }
  if (changed) saveMentoringStackToStorage();
}

function upsertMentoringGroup(group: MentoringGroupRecord) {
  const index = mentoringGroupIndex(group.id);
  if (index >= 0) {
    mentoringCache.groups[index] = group;
  } else {
    mentoringCache.groups.push(group);
  }
  saveMentoringStackToStorage();
}

function deleteMentoringGroup(groupId: string) {
  const index = mentoringGroupIndex(groupId);
  if (index < 0) return;
  mentoringCache.groups.splice(index, 1);
  if (mentoringDetailGroupId === groupId) {
    mentoringDetailGroupId = null;
    if (mentoringDetailDialogEl.open) mentoringDetailDialogEl.close();
  }
  saveMentoringStackToStorage();
}

function availableMentoringSuggestions(): MentoringCachedSuggestion[] {
  const excludeGroupId = mentoringPicker?.groupId ?? null;
  const assigned = mentoringAssignedPlayerIds(excludeGroupId);
  return mentoringCache.suggestions.filter((suggestion) =>
    suggestion.memberIds.every((id) => !assigned.has(id)),
  );
}

function mentoringVerdictText(evaluation: MentoringUnitEvaluation): string {
  const liftBits = evaluation.edges
    .flatMap((e) => e.lifts.slice(0, 2))
    .filter((label, index, all) => all.indexOf(label) === index)
    .slice(0, 3);
  return [
    evaluation.shape === "overload" || evaluation.shape === "cascade"
      ? evaluation.shape
      : evaluation.shape === "invalid"
        ? "unsafe"
        : null,
    liftBits.length ? liftBits.join(", ") : null,
    evaluation.warnings[0] ?? null,
  ]
    .filter(Boolean)
    .join(" · ");
}

function applyMentoringVerdictTone(
  el: HTMLElement,
  evaluation: MentoringUnitEvaluation,
) {
  el.className = "mentoring-verdict";
  if (
    evaluation.shape === "invalid" ||
    evaluation.warnings.some((w) => w.startsWith("Mid→Low"))
  ) {
    el.classList.add("is-bad");
  } else if (evaluation.warnings.length > 0) {
    el.classList.add("is-warn");
  }
}

function mentoringUnitMembersFromRecord(
  group: MentoringGroupRecord,
  byId: Map<string, MentoringCandidate>,
): MentoringUnitMember[] | null {
  const players = group.memberIds
    .map((id) => byId.get(id))
    .filter((row): row is MentoringCandidate => row !== undefined);
  if (players.length !== 3) return null;

  const hasAllRoles = players.every((p) => group.roles[String(p.id)]);
  if (!hasAllRoles) {
    return defaultMentoringUnitRoles(players, {
      hierarchyById: mentoringHierarchyByIdMap(),
    });
  }
  return players.map((player) => ({
    player,
    role: group.roles[String(player.id)]!,
  }));
}

function suggestionFromGroup(
  group: MentoringInfluenceSafeGroup,
): MentoringCachedSuggestion {
  const memberIds = group.members.map((m) => String(m.player.id));
  const roles: Record<string, MentoringInfluenceSeat> = {};
  for (const seat of group.members) {
    roles[String(seat.player.id)] = seat.role;
  }
  const key = [...memberIds].sort().join("|");
  return {
    id: key,
    memberIds,
    roles,
    score: group.score,
    path: `${group.shape}:${group.path}`,
    key,
  };
}

function yieldToMain(): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, 0);
  });
}

async function warmMentoringSuggestions(
  candidates: MentoringCandidate[],
  generation: number,
  options?: { pool?: MentoringCandidate[]; append?: boolean },
) {
  if (generation !== mentoringCache.generation) return;
  mentoringCache.suggestionsStatus = "loading";
  updateMentoringSuggestButton();

  await yieldToMain();
  if (generation !== mentoringCache.generation) return;

  const pool = options?.pool ?? candidates;
  let groups: MentoringInfluenceSafeGroup[] = [];
  try {
    groups = findInfluenceSafeMentoringGroups(pool, {
      max: 32,
      hierarchyById: mentoringHierarchyByIdMap(),
    });
  } catch (err) {
    console.error("Mentoring suggestion warm failed", err);
    groups = [];
  }

  if (generation !== mentoringCache.generation) return;

  const seen = new Set<string>(
    options?.append
      ? mentoringCache.suggestions.map((row) => row.key)
      : [],
  );
  const collected: MentoringCachedSuggestion[] = options?.append
    ? [...mentoringCache.suggestions]
    : [];
  for (const group of groups) {
    const row = suggestionFromGroup(group);
    if (seen.has(row.key)) continue;
    seen.add(row.key);
    collected.push(row);
  }

  mentoringCache.suggestions = collected;
  if (!options?.append) mentoringCache.suggestionCursor = 0;
  mentoringCache.suggestionsStatus = "ready";
  updateMentoringSuggestButton();
}

function mentoringSuggestionPool(
  candidates: MentoringCandidate[],
): MentoringCandidate[] {
  const excludeGroupId = mentoringPicker?.groupId ?? null;
  const assigned = mentoringAssignedPlayerIds(excludeGroupId);
  return candidates.filter((player) => !assigned.has(String(player.id)));
}

function refreshMentoringSuggestionsForPicker(append = false) {
  const candidates = ensureMentoringCacheForRoster();
  const pool = mentoringSuggestionPool(candidates);
  if (pool.length < 3) {
    if (!append) mentoringCache.suggestions = [];
    mentoringCache.suggestionsStatus = "ready";
    updateMentoringSuggestButton();
    return;
  }
  const generation = mentoringCache.generation;
  void warmMentoringSuggestions(candidates, generation, { pool, append });
}

function scheduleMentoringSuggestions(candidates: MentoringCandidate[]) {
  if (mentoringCache.suggestionsStatus === "loading") return;
  if (mentoringCache.suggestionsStatus === "ready") return;
  const generation = mentoringCache.generation;
  void warmMentoringSuggestions(candidates, generation);
}

function ensureMentoringCacheForRoster(): MentoringCandidate[] {
  const persistKey = mentoringPersistKey();
  const sessionKey = mentoringSessionKey();

  if (!persistKey || !sessionKey) {
    invalidateMentoringCache();
    return [];
  }

  if (mentoringCache.persistKey !== persistKey) {
    mentoringCache.generation += 1;
    const persisted = loadMentoringStackFromStorage(persistKey);
    mentoringCache = {
      ...emptyMentoringCache(persistKey, "", mentoringCache.generation),
      groups: persisted.groups,
      dynamicsByPlayerId: persisted.dynamicsByPlayerId,
    };
    mentoringRenderFingerprint = "";
  }

  if (mentoringCache.sessionKey !== sessionKey) {
    mentoringCache.sessionKey = sessionKey;
    mentoringCache.candidates = null;
    mentoringCache.suggestions = [];
    mentoringCache.suggestionCursor = 0;
    mentoringCache.suggestionsStatus = "idle";
    mentoringCache.generation += 1;
  }

  if (!mentoringCache.candidates) {
    mentoringCache.candidates = mentoringSuggestPool(
      firstTeamMentoringPlayers(),
    )
      .map(candidateFromRosterPlayer)
      .filter((row): row is MentoringCandidate => row !== null);
  }

  const candidates = mentoringCache.candidates;
  pruneMentoringGroups(candidates);
  scheduleMentoringSuggestions(candidates);
  return candidates;
}

function updateMentoringSuggestButton() {
  if (!mentoringPickerSuggestBtn) return;
  const available = availableMentoringSuggestions();
  if (mentoringCache.suggestionsStatus === "loading") {
    mentoringPickerSuggestBtn.disabled = true;
    mentoringPickerSuggestBtn.textContent = "Suggest…";
    return;
  }
  if (
    mentoringCache.suggestionsStatus === "ready" &&
    available.length === 0
  ) {
    mentoringPickerSuggestBtn.disabled = true;
    mentoringPickerSuggestBtn.textContent = "No ideas";
    return;
  }
  mentoringPickerSuggestBtn.disabled =
    mentoringCache.suggestionsStatus !== "ready";
  mentoringPickerSuggestBtn.textContent = "Suggest";
}

function openMentoringPicker(options?: { groupId?: string | null }) {
  ensureMentoringCacheForRoster();
  const groupId = options?.groupId ?? null;
  const group = groupId
    ? mentoringCache.groups.find((row) => row.id === groupId) ?? null
    : null;
  mentoringPicker = {
    groupId,
    selectedIds: [...(group?.memberIds ?? [])],
    builtRosterKey: null,
    shownSuggestionKeys: new Set(),
  };
  mentoringCache.suggestions = [];
  mentoringCache.suggestionCursor = 0;
  mentoringCache.suggestionsStatus = "idle";
  renderMentoringPicker(true);
  refreshMentoringSuggestionsForPicker(false);
  updateMentoringSuggestButton();
  if (!mentoringPickerDialogEl.open) mentoringPickerDialogEl.showModal();
}

function closeMentoringPicker() {
  mentoringPicker = null;
  if (mentoringPickerDialogEl.open) mentoringPickerDialogEl.close();
}

function applyMentoringPickerSelection() {
  if (!mentoringPicker) return;
  const candidates = ensureMentoringCacheForRoster();
  const byId = new Map(candidates.map((c) => [String(c.id), c]));
  const groupId = mentoringPicker.groupId;

  if (mentoringPicker.selectedIds.length !== 3) {
    if (groupId) deleteMentoringGroup(groupId);
    renderMentoringPage();
    return;
  }

  const players = mentoringPicker.selectedIds
    .map((id) => byId.get(id))
    .filter((row): row is MentoringCandidate => row !== undefined);
  if (players.length !== 3) return;

  const assignedElsewhere = mentoringAssignedPlayerIds(groupId);
  if (mentoringPicker.selectedIds.some((id) => assignedElsewhere.has(id))) {
    return;
  }

  const defaults = defaultMentoringUnitRoles(players, {
    hierarchyById: mentoringHierarchyByIdMap(),
  });
  const roles: Record<string, MentoringInfluenceSeat> = {};
  for (const seat of defaults) roles[String(seat.player.id)] = seat.role;

  const existing = groupId
    ? mentoringCache.groups.find((group) => group.id === groupId)
    : null;
  if (existing) {
    const prev = new Set(existing.memberIds);
    const sameTrio = mentoringPicker.selectedIds.every((id) => prev.has(id));
    if (sameTrio) {
      for (const id of mentoringPicker.selectedIds) {
        if (existing.roles[id]) roles[id] = existing.roles[id]!;
      }
      const seats = Object.values(roles);
      const missing =
        !seats.includes("high") ||
        !seats.includes("mid") ||
        !seats.includes("low");
      if (missing) {
        for (const seat of defaults) roles[String(seat.player.id)] = seat.role;
      }
    }
  }

  const key = [...mentoringPicker.selectedIds].sort().join("|");
  const hit = mentoringCache.suggestions.find((s) => s.key === key);
  const nextMemberIds = hit
    ? [...hit.memberIds]
    : [...mentoringPicker.selectedIds];
  const influenceEdges = mentoringEdgesForMembers(
    existing?.influenceEdges,
    nextMemberIds,
  );
  upsertMentoringGroup({
    id: groupId ?? newMentoringGroupId(),
    memberIds: nextMemberIds,
    roles: hit ? { ...hit.roles } : roles,
    ...(influenceEdges ? { influenceEdges } : {}),
  });
  if (!groupId) {
    mentoringPicker.groupId = mentoringCache.groups.at(-1)?.id ?? null;
  }
  renderMentoringPage();
}

function syncMentoringPickerRowStates() {
  if (!mentoringPicker) return;
  const selected = new Set(mentoringPicker.selectedIds);
  const full = selected.size >= 3;

  mentoringPickerCountEl.textContent = `${selected.size}/3`;

  for (const tr of mentoringPickerBodyEl.querySelectorAll("tr")) {
    const id = tr.getAttribute("data-player-id");
    if (!id) continue;
    const isOn = selected.has(id);
    const incomplete = tr.dataset.incomplete === "1";
    const blocked = incomplete || (!isOn && full);
    tr.classList.toggle("is-selected", isOn);
    tr.classList.toggle("is-disabled", blocked);
    const toggle = tr.querySelector<HTMLButtonElement>(".mentoring-picker-toggle");
    if (toggle) {
      toggle.classList.toggle("is-on", isOn);
      toggle.setAttribute("aria-pressed", isOn ? "true" : "false");
      toggle.disabled = blocked;
    }
  }
}

function setMentoringPickerSelection(ids: string[], apply = true) {
  if (!mentoringPicker) return;
  mentoringPicker.selectedIds = [...ids];
  syncMentoringPickerRowStates();
  if (apply) applyMentoringPickerSelection();
}

function toggleMentoringPickerPlayer(id: string) {
  if (!mentoringPicker) return;
  const eligible = mentoringCache.candidates?.some(
    (player) => String(player.id) === id,
  );
  if (!eligible) return;
  const selected = mentoringPicker.selectedIds.includes(id);
  if (selected) {
    mentoringPicker.selectedIds = mentoringPicker.selectedIds.filter(
      (row) => row !== id,
    );
  } else if (mentoringPicker.selectedIds.length < 3) {
    mentoringPicker.selectedIds = [...mentoringPicker.selectedIds, id];
  } else {
    return;
  }
  syncMentoringPickerRowStates();
  requestAnimationFrame(() => {
    applyMentoringPickerSelection();
  });
}

function suggestMentoringPickerSelection() {
  if (!mentoringPicker) return;
  if (mentoringCache.suggestionsStatus === "loading") return;

  let available = availableMentoringSuggestions().filter(
    (suggestion) => !mentoringPicker!.shownSuggestionKeys.has(suggestion.key),
  );

  if (available.length === 0) {
    refreshMentoringSuggestionsForPicker(true);
    available = availableMentoringSuggestions().filter(
      (suggestion) => !mentoringPicker!.shownSuggestionKeys.has(suggestion.key),
    );
    if (available.length === 0) {
      updateMentoringSuggestButton();
      return;
    }
  }

  available.sort((a, b) => b.score - a.score);
  const eligibleIds = new Set(
    (mentoringCache.candidates ?? []).map((player) => String(player.id)),
  );
  const suggestion = available.find((row) =>
    row.memberIds.every((id) => eligibleIds.has(id)),
  );
  if (!suggestion) {
    updateMentoringSuggestButton();
    return;
  }
  mentoringPicker.shownSuggestionKeys.add(suggestion.key);
  setMentoringPickerSelection(suggestion.memberIds, true);
}

function renderMentoringPicker(forceRebuild = false) {
  if (!mentoringPicker) return;
  const sessionKey = mentoringSessionKey();
  const candidates = ensureMentoringCacheForRoster().sort((a, b) =>
    a.name.localeCompare(b.name),
  );
  const assignedElsewhere = mentoringAssignedPlayerIds(mentoringPicker.groupId);
  const visibleCandidates = candidates.filter(
    (player) => !assignedElsewhere.has(String(player.id)),
  );
  const incompletePool = firstTeamMentoringPlayers()
    .filter((player) => !isMentoringCompleteEnough(player))
    .sort((a, b) =>
      (rosterResolvedName(a) ?? a.name ?? "").localeCompare(
        rosterResolvedName(b) ?? b.name ?? "",
        undefined,
        { sensitivity: "base" },
      ),
    );

  const rosterAssignedKey = [
    sessionKey,
    [...assignedElsewhere].sort().join("|"),
    incompletePool.map((p) => String(p.uid)).join("|"),
  ].join("::");

  const needsBuild =
    forceRebuild ||
    mentoringPicker.builtRosterKey !== rosterAssignedKey ||
    mentoringPickerBodyEl.childElementCount === 0;

  if (needsBuild) {
    mentoringPicker.builtRosterKey = rosterAssignedKey;
    const frag = document.createDocumentFragment();
    for (const player of visibleCandidates) {
      const id = String(player.id);
      const tr = document.createElement("tr");
      tr.dataset.playerId = id;

      const selTd = document.createElement("td");
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "mentoring-picker-toggle";
      toggle.dataset.playerId = id;
      toggle.setAttribute("aria-label", `Toggle ${player.name}`);
      selTd.append(toggle);

      const nameTd = document.createElement("td");
      nameTd.textContent = player.name;
      const ageTd = document.createElement("td");
      ageTd.textContent = player.age !== undefined ? String(player.age) : "—";
      const persTd = document.createElement("td");
      persTd.textContent = player.personality ?? "—";
      const detTd = document.createElement("td");
      detTd.textContent =
        player.determination !== undefined ? String(player.determination) : "—";
      const leadTd = document.createElement("td");
      leadTd.textContent =
        player.leadership !== undefined ? String(player.leadership) : "—";

      tr.append(selTd, nameTd, ageTd, persTd, detTd, leadTd);
      frag.append(tr);
    }
    for (const player of incompletePool) {
      const id = String(player.uid);
      const trust = playerExtractTrust(player);
      const holes = extractTrustHoles(trust);
      const tr = document.createElement("tr");
      tr.dataset.playerId = id;
      tr.dataset.incomplete = "1";
      tr.classList.add("is-incomplete", "is-disabled");
      tr.title = holes.join(" · ");

      const selTd = document.createElement("td");
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "mentoring-picker-toggle";
      toggle.dataset.playerId = id;
      toggle.disabled = true;
      toggle.setAttribute("aria-label", "Incomplete extract — cannot seat");
      selTd.append(toggle);

      const nameTd = document.createElement("td");
      nameTd.textContent = rosterResolvedName(player) ?? "Name missing";
      const ageTd = document.createElement("td");
      const age = rosterPlayerAge(player, rosterMeta.gameDate);
      ageTd.textContent = age != null ? String(age) : "—";
      const persTd = document.createElement("td");
      persTd.textContent = "Incomplete";
      const detTd = document.createElement("td");
      detTd.textContent = "—";
      const leadTd = document.createElement("td");
      leadTd.textContent = "—";

      tr.append(selTd, nameTd, ageTd, persTd, detTd, leadTd);
      frag.append(tr);
    }
    mentoringPickerBodyEl.replaceChildren(frag);
  }

  syncMentoringPickerRowStates();
  updateMentoringSuggestButton();
}

function createMentoringPlayerFace(uid: string): {
  wrap: HTMLDivElement;
  img: HTMLImageElement;
} {
  const wrap = document.createElement("div");
  wrap.className = "mentoring-seat-face-wrap has-no-face";

  const img = document.createElement("img");
  img.className = "mentoring-seat-face";
  img.alt = "";
  img.decoding = "async";
  bindPlayerFace(img, uid, {
    onReady: () => wrap.classList.remove("has-no-face"),
    onMissing: () => wrap.classList.add("has-no-face"),
  });

  wrap.append(img);
  return { wrap, img };
}

function renderMentoringDetailSeats(
  host: HTMLElement,
  members: MentoringUnitMember[],
  options?: {
    interactive?: boolean;
    group?: MentoringGroupRecord | null;
  },
) {
  host.replaceChildren();
  const ordered = ["high", "mid", "low"].map(
    (seat) => members.find((m) => m.role === seat)!,
  );
  for (const seat of ordered) {
    if (!seat) continue;
    const playerId = String(seat.player.id);
    const state = mentoringMemberDynamicsState(playerId, options?.group);

    const wrap = document.createElement("div");
    wrap.className = "mentoring-seat";
    wrap.dataset.playerId = playerId;

    const card = document.createElement(
      options?.interactive ? "button" : "div",
    );
    card.className = `mentoring-seat-card is-dynamics-${state}`;
    card.dataset.playerId = playerId;
    if (options?.interactive) {
      (card as HTMLButtonElement).type = "button";
      card.setAttribute(
        "aria-label",
        `${seat.player.name}: Dynamics ${state === "complete" ? "collected" : state === "partial" ? "partial" : "missing"}. Hover for attributes, click for Dynamics.`,
      );
      card.addEventListener("click", (event) => {
        event.stopPropagation();
        hideMetricTip();
        openMentoringDynamicsModal(playerId, options?.group?.id ?? null);
      });
    }

    const { wrap: faceWrap } = createMentoringPlayerFace(playerId);
    const fallback = document.createElement("span");
    fallback.className = "mentoring-seat-face-fallback";
    fallback.textContent = mentoringLastName(seat.player.name)
      .slice(0, 1)
      .toUpperCase();
    faceWrap.append(fallback);

    const meta = document.createElement("div");
    meta.className = "mentoring-seat-meta";

    const name = document.createElement("p");
    name.className = "mentoring-seat-name";
    name.textContent = seat.player.name;
    name.title = seat.player.name;

    const dyn = document.createElement("span");
    dyn.className = `mentoring-seat-dynamics is-${state}`;
    const label = getMentoringDynamicsLabel(playerId);
    dyn.textContent =
      state === "complete"
        ? dynamicsShortSummary(label)
        : state === "partial"
          ? "Dynamics · partial"
          : "Dynamics · missing";

    meta.append(name, dyn);
    card.append(faceWrap, meta);
    wrap.append(card);
    host.append(wrap);
  }
}

function dynamicsShortSummary(label: MentoringDynamicsLabel): string {
  const bits: string[] = [];
  if (label.hierarchy === "teamLeader") bits.push("Leader");
  else if (label.hierarchy === "highlyInfluential") bits.push("HI");
  else if (label.hierarchy === "influential") bits.push("Inf");
  else if (label.hierarchy === "other") bits.push("Other");
  else if (label.hierarchy === "na") bits.push("N/A");

  if (label.socialGroup === "core") bits.push("Core");
  else if (label.socialGroup === "secondaryA") bits.push("Sec A");
  else if (label.socialGroup === "secondaryB") bits.push("Sec B");
  else if (label.socialGroup === "secondaryC") bits.push("Sec C");
  else if (label.socialGroup === "other") bits.push("Soc Other");

  if (label.captaincy === "captain") bits.push("C");
  else if (label.captaincy === "viceCaptain") bits.push("VC");

  return bits.join(" · ") || "Dynamics · collected";
}

function renderMentoringGroupPanel(
  shell: HTMLElement,
  members: MentoringUnitMember[],
  group: MentoringGroupRecord,
) {
  shell.replaceChildren();

  const seats = document.createElement("div");
  seats.className = "mentoring-seats";
  const influencers = mentoringGroupTableInfluencers(members);
  const receivers = mentoringGroupTableReceivers(members);
  const canShowAttrs = influencers.length > 0 && receivers.length > 0;

  renderMentoringDetailSeats(seats, members, {
    interactive: true,
    group,
  });

  // Overview = face + name only. Full HA×player matrix (with deltas) on seat hover.
  if (canShowAttrs) {
    for (const card of seats.querySelectorAll<HTMLElement>(
      ".mentoring-seat-card[data-player-id]",
    )) {
      const playerId = card.dataset.playerId;
      if (!playerId) continue;
      card.classList.add("has-attrs-tip");
      card.removeAttribute("title");
      wireMentoringMatrixTip(card, () =>
        createMentoringGroupTable(influencers, receivers, playerId),
      );
    }
  }
  shell.append(seats);
}

function renderMentoringDetailModal(groupId: string) {
  const candidates = ensureMentoringCacheForRoster();
  const group = mentoringCache.groups.find((row) => row.id === groupId);
  if (!group) return;

  const byId = new Map(candidates.map((c) => [String(c.id), c]));
  const members = mentoringUnitMembersFromRecord(group, byId);
  const index = mentoringGroupIndex(group.id);
  mentoringDetailTitleEl.textContent = mentoringGroupLabel(index);

  if (!members) {
    mentoringDetailVerdictEl.textContent =
      "This group is missing players from the current Career Save.";
    mentoringDetailVerdictEl.className = "mentoring-verdict is-warn";
    mentoringDetailSeatsEl.replaceChildren();
    mentoringDetailAttrsEl.replaceChildren();
    return;
  }

  const evaluation = evaluateMentoringUnit(members);
  applyMentoringVerdictTone(mentoringDetailVerdictEl, evaluation);
  mentoringDetailVerdictEl.textContent = mentoringVerdictText(evaluation);
  renderMentoringDetailSeats(mentoringDetailSeatsEl, members, {
    interactive: true,
    group,
  });
  mentoringDetailAttrsEl.replaceChildren();
  const influencers = mentoringGroupTableInfluencers(members);
  const receivers = mentoringGroupTableReceivers(members);
  if (influencers.length && receivers.length) {
    mentoringDetailAttrsEl.append(
      createMentoringGroupTable(influencers, receivers),
    );
  }
}

function openMentoringDetailModal(groupId: string) {
  mentoringDetailGroupId = groupId;
  renderMentoringDetailModal(groupId);
  if (!mentoringDetailDialogEl.open) mentoringDetailDialogEl.showModal();
}

function closeMentoringDetailModal() {
  mentoringDetailGroupId = null;
  if (mentoringDetailDialogEl.open) mentoringDetailDialogEl.close();
}

function syncMentoringDynamicsModalUi() {
  if (!mentoringDynamicsDraft) return;
  const draft = mentoringDynamicsDraft;
  const state = mentoringDynamicsState(draft, draft.influenceByPeerId);
  mentoringDynamicsStatusEl.className = `mentoring-dynamics-status is-${state}`;
  mentoringDynamicsStatusEl.textContent =
    state === "complete"
      ? "Collected — Dynamics + mentoring influence labeled"
      : state === "partial"
        ? "Partial — finish Dynamics and triangle influence from FM"
        : "Missing — copy Dynamics + influence arrows from FM";

  for (const group of mentoringDynamicsDialogEl.querySelectorAll<HTMLElement>(
    ".mentoring-dynamics-options[data-field]",
  )) {
    const field = group.dataset.field as
      | "captaincy"
      | "hierarchy"
      | "socialGroup"
      | undefined;
    if (!field || field === undefined) continue;
    if (field !== "captaincy" && field !== "hierarchy" && field !== "socialGroup") {
      continue;
    }
    const current = draft[field];
    for (const btn of group.querySelectorAll<HTMLButtonElement>("button")) {
      const on = btn.dataset.value === current;
      btn.classList.toggle("is-on", on);
      btn.setAttribute("aria-pressed", String(on));
    }
  }

  for (const group of mentoringDynamicsInfluenceEl.querySelectorAll<HTMLElement>(
    ".mentoring-dynamics-options[data-peer-id]",
  )) {
    const peerId = group.dataset.peerId;
    const dir = group.dataset.dir as "on" | "from" | undefined;
    if (!peerId || (dir !== "on" && dir !== "from")) continue;
    const peer = draft.influenceByPeerId[peerId];
    const current = peer?.[dir] ?? null;
    for (const btn of group.querySelectorAll<HTMLButtonElement>("button")) {
      const on = btn.dataset.value === current;
      btn.classList.toggle("is-on", on);
      btn.setAttribute("aria-pressed", String(on));
    }
  }
}

function buildMentoringInfluenceFields(
  playerId: string,
  influenceByPeerId: Record<string, MentoringPeerInfluenceDraft>,
) {
  mentoringDynamicsInfluenceEl.replaceChildren();
  const peerIds = Object.keys(influenceByPeerId);
  if (peerIds.length === 0) {
    mentoringDynamicsInfluenceEl.hidden = true;
    return;
  }

  mentoringDynamicsInfluenceEl.hidden = false;
  const candidates = ensureMentoringCacheForRoster();
  const byId = new Map(candidates.map((c) => [String(c.id), c]));

  const heading = document.createElement("p");
  heading.className = "mentoring-dynamics-influence-heading";
  heading.textContent = "Mentoring influence (triangle arrows)";
  mentoringDynamicsInfluenceEl.append(heading);

  const levels: { value: MentoringInfluenceLevel; label: string }[] = [
    { value: "none", label: "None" },
    { value: "light", label: "Light" },
    { value: "average", label: "Average" },
    { value: "significant", label: "Significant" },
  ];

  for (const peerId of peerIds) {
    const peerName = byId.get(peerId)?.name ?? peerId;
    const block = document.createElement("div");
    block.className = "mentoring-dynamics-influence-peer";

    const peerTitle = document.createElement("p");
    peerTitle.className = "mentoring-dynamics-influence-peer-name";
    peerTitle.textContent = peerName;
    block.append(peerTitle);

    for (const dir of ["on", "from"] as const) {
      const fieldset = document.createElement("fieldset");
      fieldset.className = "mentoring-dynamics-field";
      const legend = document.createElement("legend");
      legend.textContent =
        dir === "on"
          ? `Influence on ${peerName}`
          : `Influence from ${peerName}`;
      const options = document.createElement("div");
      options.className = "mentoring-dynamics-options";
      options.dataset.peerId = peerId;
      options.dataset.dir = dir;
      options.dataset.subjectId = playerId;
      for (const level of levels) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.dataset.value = level.value;
        btn.textContent = level.label;
        options.append(btn);
      }
      fieldset.append(legend, options);
      block.append(fieldset);
    }

    mentoringDynamicsInfluenceEl.append(block);
  }
}

function openMentoringDynamicsModal(
  playerId: string,
  groupId: string | null = null,
) {
  const candidates = ensureMentoringCacheForRoster();
  const player = candidates.find((row) => String(row.id) === playerId);
  if (!player) return;

  const group =
    (groupId
      ? mentoringCache.groups.find((row) => row.id === groupId)
      : null) ??
    (mentoringDetailGroupId
      ? mentoringCache.groups.find((row) => row.id === mentoringDetailGroupId)
      : null) ??
    null;

  mentoringDynamicsPlayerId = playerId;
  mentoringDynamicsGroupId = group?.id ?? null;
  const base = getMentoringDynamicsLabel(playerId);
  mentoringDynamicsDraft = {
    ...emptyMentoringDynamicsDraft(),
    ...base,
    influenceByPeerId: mentoringMemberInfluenceFromGroup(group, playerId),
  };
  mentoringDynamicsTitleEl.textContent = player.name;
  mentoringDynamicsSubtitleEl.textContent = group
    ? "Label from FM Dynamics + mentoring group influence arrows"
    : "Label from FM Dynamics (Captains / Hierarchy / Social Groups)";
  buildMentoringInfluenceFields(playerId, mentoringDynamicsDraft.influenceByPeerId);
  syncMentoringDynamicsModalUi();
  if (!mentoringDynamicsDialogEl.open) mentoringDynamicsDialogEl.showModal();
}

function closeMentoringDynamicsModal() {
  mentoringDynamicsPlayerId = null;
  mentoringDynamicsGroupId = null;
  mentoringDynamicsDraft = null;
  mentoringDynamicsInfluenceEl.replaceChildren();
  mentoringDynamicsInfluenceEl.hidden = true;
  if (mentoringDynamicsDialogEl.open) mentoringDynamicsDialogEl.close();
}

function saveMentoringDynamicsModal() {
  if (!mentoringDynamicsPlayerId || !mentoringDynamicsDraft) return;
  const candidates = ensureMentoringCacheForRoster();
  const player = candidates.find(
    (row) => String(row.id) === mentoringDynamicsPlayerId,
  );
  const { influenceByPeerId, ...dynamicsFields } = mentoringDynamicsDraft;
  const next: MentoringDynamicsLabel = {
    captaincy: dynamicsFields.captaincy,
    hierarchy: dynamicsFields.hierarchy,
    socialGroup: dynamicsFields.socialGroup,
    labeledAt: new Date().toISOString(),
    ...(player
      ? { snapshot: mentoringDynamicsSnapshotFromCandidate(player) }
      : {}),
  };

  if (
    next.captaincy == null &&
    next.hierarchy == null &&
    next.socialGroup == null
  ) {
    delete mentoringCache.dynamicsByPlayerId[mentoringDynamicsPlayerId];
  } else {
    mentoringCache.dynamicsByPlayerId[mentoringDynamicsPlayerId] = next;
  }

  if (mentoringDynamicsGroupId) {
    const group = mentoringCache.groups.find(
      (row) => row.id === mentoringDynamicsGroupId,
    );
    if (group) {
      const edges = { ...(group.influenceEdges ?? {}) };
      for (const [peerId, peer] of Object.entries(influenceByPeerId)) {
        const onKey = mentoringInfluenceEdgeKey(
          mentoringDynamicsPlayerId,
          peerId,
        );
        const fromKey = mentoringInfluenceEdgeKey(
          peerId,
          mentoringDynamicsPlayerId,
        );
        if (peer.on == null) delete edges[onKey];
        else edges[onKey] = peer.on;
        if (peer.from == null) delete edges[fromKey];
        else edges[fromKey] = peer.from;
      }
      if (Object.keys(edges).length === 0) delete group.influenceEdges;
      else group.influenceEdges = edges;
    }
  }

  saveMentoringStackToStorage();
  // Labels can change Suggest seating — refresh pool next open.
  mentoringCache.suggestions = [];
  mentoringCache.suggestionCursor = 0;
  mentoringCache.suggestionsStatus = "idle";
  mentoringRenderFingerprint = "";
  closeMentoringDynamicsModal();
  renderMentoringPage();
  if (mentoringDetailGroupId) renderMentoringDetailModal(mentoringDetailGroupId);
}

function createMentoringIconButton(
  label: string,
  pathD: string,
  danger = false,
): HTMLButtonElement {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = danger
    ? "btn-icon btn-danger mentoring-card-icon-btn"
    : "btn-icon mentoring-card-icon-btn";
  btn.setAttribute("aria-label", label);
  btn.title = label;

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 16 16");
  svg.setAttribute("width", "14");
  svg.setAttribute("height", "14");
  svg.setAttribute("aria-hidden", "true");

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("fill", "currentColor");
  path.setAttribute("d", pathD);
  svg.append(path);
  btn.append(svg);
  return btn;
}

function createMentoringGroupCard(
  group: MentoringGroupRecord,
  index: number,
  candidates: MentoringCandidate[],
  dense = false,
) {
  const byId = new Map(candidates.map((c) => [String(c.id), c]));
  const members = mentoringUnitMembersFromRecord(group, byId);

  const card = document.createElement("article");
  card.className = "mentoring-card";
  if (dense) card.classList.add("is-dense");
  card.dataset.groupId = group.id;

  const head = document.createElement("div");
  head.className = "mentoring-card-head";

  const title = document.createElement("p");
  title.className = "mentoring-card-title";
  title.textContent = mentoringGroupLabel(index);

  const coverage = document.createElement("span");
  coverage.className = "mentoring-card-dynamics-coverage";
  if (members) {
    const states = members.map((seat) =>
      mentoringMemberDynamicsState(String(seat.player.id), group),
    );
    const complete = states.filter((s) => s === "complete").length;
    const partial = states.filter((s) => s === "partial").length;
    const missing = states.length - complete - partial;
    if (complete === states.length) {
      coverage.classList.add("is-complete");
      coverage.textContent = "Dynamics complete";
    } else if (complete + partial > 0) {
      coverage.classList.add("is-partial");
      coverage.textContent = `Dynamics ${complete}/${states.length}`;
    } else {
      coverage.classList.add("is-missing");
      coverage.textContent = missing > 0 ? "Dynamics missing" : "Dynamics —";
    }
  } else {
    coverage.classList.add("is-missing");
    coverage.textContent = "Dynamics —";
  }

  const actions = document.createElement("div");
  actions.className = "mentoring-card-actions";
  const editBtn = createMentoringIconButton(
    "Edit group",
    "M11.013 1.427a1.75 1.75 0 0 1 2.474 0l1.086 1.086a1.75 1.75 0 0 1 0 2.474l-8.61 8.61a.25.25 0 0 1-.177.073H3.25A.75.75 0 0 1 2.5 12.75v-1.586a.25.25 0 0 1 .073-.177l8.61-8.61z",
  );
  editBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    openMentoringPicker({ groupId: group.id });
  });
  const deleteBtn = createMentoringIconButton(
    "Delete group",
    "M6.5 1.75a.25.25 0 0 1 .25-.25h2.5a.25.25 0 0 1 .25.25V3h-3V1.75zm4.5 1.5V1.75a1.75 1.75 0 0 0-1.75-1.75h-2.5A1.75 1.75 0 0 0 4.75 1.75V3.25H2v1.5h12v-1.5H11zM4.496 6.675l.66 6.6a.25.25 0 0 0 .249.225h5.19a.25.25 0 0 0 .249-.225l.66-6.6a.75.75 0 0 1 1.492.149l-.66 6.6A1.748 1.748 0 0 1 10.595 15h-5.19a1.75 1.75 0 0 1-1.741-1.575l-.66-6.6a.75.75 0 0 1 1.492-.15z",
    true,
  );
  deleteBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    deleteMentoringGroup(group.id);
    renderMentoringPage();
  });
  actions.append(editBtn, deleteBtn);
  head.append(title, coverage, actions);
  card.append(head);

  if (members) {
    const shell = document.createElement("div");
    shell.className = "mentoring-card-shell";
    renderMentoringGroupPanel(shell, members, group);
    card.append(shell);
  } else {
    const empty = document.createElement("p");
    empty.className = "mentoring-card-empty";
    empty.textContent = "—";
    card.append(empty);
  }

  return card;
}

function renderMentoringPage() {
  if (squadViewMode !== "mentoring") return;

  if (rosterMeta.source !== "save" || rosterPlayers.length === 0) {
    mentoringCardsEl.replaceChildren();
    mentoringCardsEl.classList.remove("is-dense");
    mentoringEmptyEl.hidden = false;
    mentoringEmptyEl.textContent = "Load a Career Save";
    mentoringAddBtn.disabled = true;
    mentoringStatusEl.textContent = "Load a Career Save";
    mentoringRenderFingerprint = "";
    return;
  }

  const candidates = ensureMentoringCacheForRoster();
  const dense =
    mentoringCache.groups.length >= MENTORING_DENSE_GROUP_THRESHOLD;
  const fingerprint = JSON.stringify({
    persist: mentoringCache.persistKey,
    session: mentoringCache.sessionKey,
    groups: mentoringCache.groups,
    dynamics: mentoringCache.dynamicsByPlayerId,
    canCreatePool: candidates.length,
    dense,
    // Bust card DOM when overview drops on-card attr matrix (T021).
    attrUi: "seat-fill-tip-v1",
  });

  const maxGroups = mentoringMaxGroups(candidates);
  const canCreate =
    candidates.length >= 3 &&
    mentoringCache.groups.length < maxGroups &&
    mentoringAssignedPlayerIds().size + 3 <= candidates.length;
  mentoringAddBtn.disabled = !canCreate;
  mentoringAddBtn.title = canCreate
    ? ""
    : mentoringCache.groups.length >= maxGroups
      ? `Max ${maxGroups} groups for this squad`
      : "Need 3 unassigned players";

  mentoringEmptyEl.hidden = mentoringCache.groups.length > 0;
  const incompleteCount = firstTeamMentoringPlayers().filter(
    (player) => !isMentoringCompleteEnough(player),
  ).length;
  mentoringEmptyEl.textContent =
    candidates.length === 0
      ? incompleteCount > 0
        ? "No complete-enough players for Mentoring"
        : "No personality data"
      : "No mentoring groups yet";

  mentoringStatusEl.textContent =
    mentoringCache.groups.length === 0
      ? incompleteCount > 0
        ? `No groups · ${incompleteCount} incomplete`
        : "No groups"
      : `${mentoringCache.groups.length} group${mentoringCache.groups.length === 1 ? "" : "s"}`;

  // Avoid tearing down face imgs on every roster refresh / disk poll.
  if (
    fingerprint === mentoringRenderFingerprint &&
    mentoringCardsEl.childElementCount === mentoringCache.groups.length
  ) {
    return;
  }
  mentoringRenderFingerprint = fingerprint;

  mentoringCardsEl.classList.toggle("is-dense", dense);
  mentoringCardsEl.replaceChildren();
  mentoringCache.groups.forEach((group, index) => {
    mentoringCardsEl.append(
      createMentoringGroupCard(group, index, candidates, dense),
    );
  });
}

mentoringAddBtn.addEventListener("click", () => openMentoringPicker({ groupId: null }));
mentoringPickerBodyEl.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof Element)) return;
  const toggle = target.closest<HTMLButtonElement>(".mentoring-picker-toggle");
  if (!toggle || toggle.disabled) return;
  const id = toggle.dataset.playerId;
  if (!id) return;
  event.preventDefault();
  toggleMentoringPickerPlayer(id);
});
mentoringPickerSuggestBtn.addEventListener("click", () => {
  suggestMentoringPickerSelection();
});
mentoringPickerClearBtn.addEventListener("click", () => {
  if (!mentoringPicker) return;
  setMentoringPickerSelection([], true);
});
mentoringPickerCloseBtn.addEventListener("click", () => closeMentoringPicker());
mentoringPickerDialogEl.addEventListener("cancel", (event) => {
  event.preventDefault();
  closeMentoringPicker();
});
mentoringDetailCloseBtn.addEventListener("click", () => closeMentoringDetailModal());
mentoringDetailDialogEl.addEventListener("cancel", (event) => {
  event.preventDefault();
  closeMentoringDetailModal();
});

mentoringDynamicsCloseBtn.addEventListener("click", () => closeMentoringDynamicsModal());
mentoringDynamicsDialogEl.addEventListener("cancel", (event) => {
  event.preventDefault();
  closeMentoringDynamicsModal();
});
mentoringDynamicsClearBtn.addEventListener("click", () => {
  if (!mentoringDynamicsDraft) return;
  const peers = Object.keys(mentoringDynamicsDraft.influenceByPeerId);
  mentoringDynamicsDraft = emptyMentoringDynamicsDraft();
  for (const peerId of peers) {
    mentoringDynamicsDraft.influenceByPeerId[peerId] = {
      on: null,
      from: null,
    };
  }
  syncMentoringDynamicsModalUi();
});
mentoringDynamicsSaveBtn.addEventListener("click", () => saveMentoringDynamicsModal());
mentoringDynamicsDialogEl.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof Element)) return;
  const btn = target.closest<HTMLButtonElement>(
    ".mentoring-dynamics-options button",
  );
  if (!btn || !mentoringDynamicsDraft) return;
  const group = btn.closest<HTMLElement>(".mentoring-dynamics-options");
  if (!group) return;
  const value = btn.dataset.value;
  if (!value) return;
  event.preventDefault();

  const peerId = group.dataset.peerId;
  const dir = group.dataset.dir as "on" | "from" | undefined;
  if (peerId && (dir === "on" || dir === "from")) {
    if (!isMentoringEdgeLevel(value)) return;
    const peer =
      mentoringDynamicsDraft.influenceByPeerId[peerId] ?? {
        on: null,
        from: null,
      };
    peer[dir] = peer[dir] === value ? null : value;
    mentoringDynamicsDraft.influenceByPeerId[peerId] = peer;
    syncMentoringDynamicsModalUi();
    return;
  }

  const field = group.dataset.field as
    | "captaincy"
    | "hierarchy"
    | "socialGroup"
    | undefined;
  if (!field) return;

  if (field === "captaincy" && isMentoringCaptaincyLabel(value)) {
    mentoringDynamicsDraft.captaincy =
      mentoringDynamicsDraft.captaincy === value ? null : value;
  } else if (field === "hierarchy" && isMentoringHierarchyLabel(value)) {
    mentoringDynamicsDraft.hierarchy =
      mentoringDynamicsDraft.hierarchy === value ? null : value;
  } else if (field === "socialGroup" && isMentoringSocialGroupLabel(value)) {
    mentoringDynamicsDraft.socialGroup =
      mentoringDynamicsDraft.socialGroup === value ? null : value;
  }
  syncMentoringDynamicsModalUi();
});


/** Re-render mentoring / attributes / loans side views after roster data changes. */
function refreshActiveSquadSideView() {
  if (squadViewMode === "mentoring") renderMentoringPage();
  else if (squadViewMode === "loans") renderLoansPage();
  else if (isSquadUnitMode(squadViewMode) && squadUnitView === "attributes") {
    setSquadViewMode(squadViewMode);
  } else if (isSquadUnitMode(squadViewMode)) renderRoster();
}

function isProbeOpen(): boolean {
  return checkerDialogEl.open;
}

const PROBE_NUDGE_KEY = "fmt.probeNudgeDismissed";

function shouldShowProbeNudge(): boolean {
  try {
    return window.localStorage.getItem(PROBE_NUDGE_KEY) !== "1";
  } catch {
    return true;
  }
}

function dismissProbeNudge() {
  try {
    window.localStorage.setItem(PROBE_NUDGE_KEY, "1");
  } catch {
    // ignore private-mode / quota failures
  }
  for (const slot of rankerPodiumEl.querySelectorAll(".is-probe-nudge")) {
    slot.classList.remove("is-probe-nudge");
  }
  for (const nudge of rankerPodiumEl.querySelectorAll(".ranker-probe-nudge")) {
    nudge.remove();
  }
}

function createProbeNudge(): HTMLElement {
  const nudge = document.createElement("div");
  nudge.className = "ranker-probe-nudge";
  nudge.setAttribute("aria-hidden", "true");

  const arrow = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  arrow.setAttribute("class", "ranker-probe-nudge-arrow");
  arrow.setAttribute("viewBox", "0 0 16 20");
  arrow.setAttribute("width", "16");
  arrow.setAttribute("height", "20");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute(
    "d",
    "M8 1.5v11.2M8 1.5 3.8 5.4M8 1.5l4.2 3.9M3.2 17.2h9.6",
  );
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "currentColor");
  path.setAttribute("stroke-width", "1.4");
  path.setAttribute("stroke-linecap", "round");
  path.setAttribute("stroke-linejoin", "round");
  arrow.append(path);

  const label = document.createElement("p");
  label.className = "ranker-probe-nudge-label";
  label.textContent = "Click to probe";

  nudge.append(arrow, label);
  return nudge;
}

let suppressProbeHashRestore = false;

function syncProbeHash(open: boolean) {
  const nextHash = !open
    ? "#rank"
    : probeMode === "compare"
      ? "#compare"
      : "#checker";
  if (window.location.hash !== nextHash) {
    window.history.replaceState(
      null,
      "",
      `${window.location.pathname}${window.location.search}${nextHash}`,
    );
  }
}

const SEO_TITLE_RANK = "Best Player Personalities | FMT";
const SEO_TITLE_ROSTER = "Squad Analyzer | FMT";
const SEO_TITLE_PROBE =
  "FM26 Hidden Attributes Calculator | FMT";
const SEO_TITLE_COMPARE =
  "Compare FM26 Personalities | Hidden Attributes | FMT";

const SEO_DESC_RANK =
  "Football Manager 26 tools: rank the best player personalities by hidden attributes, and calculate likely hidden attribute bands from personality and media handling.";
const SEO_DESC_ROSTER =
  "Football Manager 26 squad analyzer — personalities, mentoring groups, and attribute feedback from your Career Save.";
const SEO_DESC_PROBE =
  "FM26 hidden attributes calculator. Enter player personality, media handling, age, Determination and Leadership to estimate likely hidden attribute mids and bands.";
const SEO_DESC_COMPARE =
  "Compare Football Manager 26 player personalities and media handling side by side to see estimated hidden attribute bands.";

function syncDocumentSeo() {
  const meta = document.querySelector('meta[name="description"]');
  if (isProbeOpen()) {
    if (probeMode === "compare") {
      document.title = SEO_TITLE_COMPARE;
      meta?.setAttribute("content", SEO_DESC_COMPARE);
    } else {
      document.title = SEO_TITLE_PROBE;
      meta?.setAttribute("content", SEO_DESC_PROBE);
    }
    return;
  }
  if (activeTool === "roster") {
    document.title = SEO_TITLE_ROSTER;
    meta?.setAttribute("content", SEO_DESC_ROSTER);
    return;
  }
  document.title = SEO_TITLE_RANK;
  meta?.setAttribute("content", SEO_DESC_RANK);
}

function syncProbeModeChrome() {
  checkerDialogEl.dataset.probeMode = probeMode;
  for (const btn of probeModeEl.querySelectorAll<HTMLButtonElement>(
    "[data-probe-mode]",
  )) {
    const pressed = btn.dataset.probeMode === probeMode;
    btn.setAttribute("aria-pressed", String(pressed));
  }
  checkerEl.hidden = probeMode !== "single";
  compareEl.hidden = probeMode !== "compare";
  if (probeMode === "compare") {
    probeTitleFocusEl.textContent = "Compare Player Personalities";
    probeLedeEl.textContent =
      "Compare player hidden attributes from personality and media handling style";
  } else {
    probeTitleFocusEl.textContent = "Hidden Attributes Calculator";
    probeLedeEl.textContent =
      "Estimate player hidden attributes from personality and media handling style";
  }
  syncDocumentSeo();
}

/** Copy the single-probe form into Compare slot 1; leave other slots intact. */
function seedCompareSlotFromChecker(index = 0) {
  ensureCompareSlots();
  while (compareSlots.length <= index) compareSlots.push(emptyCompareSlot());
  const current = compareSlots[index]!;
  compareSlots[index] = {
    ...current,
    personality: checkPersonalityEl.value.trim(),
    mediaHandling: checkMediaEl.value.trim(),
    determination: checkDeterminationEl.value,
    leadership: checkLeadershipEl.value,
    age: checkAgeEl.value,
    isRegen: checkIsRegenEl.checked,
  };
  delete compareSlots[index]!.sourceSaveId;
  delete compareSlots[index]!.sourcePlayerId;
  persistCompareDraft();
}

function setProbeMode(
  mode: ProbeMode,
  options?: { seedFromSingle?: boolean },
) {
  probeMode = mode;
  syncProbeModeChrome();
  syncProbeHash(isProbeOpen());
  if (mode === "compare") {
    if (options?.seedFromSingle !== false) seedCompareSlotFromChecker(0);
    renderCompareSlots();
    runCompareEstimates();
    return;
  }
  runCheckEstimate();
}

/** HAS Rank detail modal (ex Attributes / Compare pages). */
function openProbe(options?: { mode?: ProbeMode; seedCompare?: boolean }) {
  if (activeTool !== "rank") {
    activeTool = "rank";
    try {
      window.localStorage.setItem(TOOL_STORAGE_KEY, "rank");
    } catch {
      // ignore private-mode / quota failures
    }
    syncToolView();
  }
  if (!checkerDialogEl.open) {
    checkerDialogEl.showModal();
  }
  dismissProbeNudge();
  const mode = options?.mode ?? "single";
  // Seed Compare slot 1 from Single when opening Single (row click / Probe).
  // Skip when restoring a Compare deep link so drafted slots stay intact.
  const seedCompare = options?.seedCompare ?? mode === "single";
  if (seedCompare) seedCompareSlotFromChecker(0);
  setProbeMode(mode, { seedFromSingle: false });
}

function closeProbe(options?: { restoreHash?: boolean }) {
  const restoreHash = options?.restoreHash !== false;
  if (!restoreHash) suppressProbeHashRestore = true;
  try {
    if (checkerDialogEl.open) checkerDialogEl.close();
    else if (restoreHash) syncProbeHash(false);
  } finally {
    suppressProbeHashRestore = false;
  }
  syncDocumentSeo();
}

function syncToolView() {
  rankEl.hidden = activeTool !== "rank";
  rosterEl.hidden = activeTool !== "roster";

  shellEl.dataset.tool = activeTool;
  // Mentoring no longer uses the history probe drawer.
  shellEl.dataset.drawer = "off";
  // Clear first-paint boot skeletons / tool restore markers.
  delete document.documentElement.dataset.boot;
  delete document.documentElement.dataset.bootTool;
  delete document.documentElement.dataset.bootRosterCount;
  delete document.documentElement.dataset.bootRosterClub;
  delete document.documentElement.dataset.bootRankDensity;

  // FMT brand remains a home shortcut; aria-current lives on the tool nav.
  appBrandEl.removeAttribute("aria-current");

  for (const btn of toolNavEl.querySelectorAll<HTMLButtonElement>("[data-tool]")) {
    const isCurrent = btn.dataset.tool === activeTool;
    if (isCurrent) btn.setAttribute("aria-current", "page");
    else btn.removeAttribute("aria-current");
  }

  document.documentElement.dataset.tool = activeTool;
  if (activeTool === "rank") scheduleRankerDensitySync();
  if (activeTool === "roster") {
    const restoreView = pendingSquadViewMode;
    const restoreUnitView = pendingSquadUnitView;
    pendingSquadViewMode = null;
    pendingSquadUnitView = null;
    if (restoreUnitView) squadUnitView = restoreUnitView;
    // Always sync chrome + personality grid first. Side-tab restores alone
    // left `.is-empty-roster` on the panel (display:none !important on
    // Attributes / Mentoring).
    syncActiveSquadPlayers();
    renderRoster();
    const view =
      restoreView && clubPlayerCount() > 0 ? restoreView : squadViewMode;
    if (view !== "firstTeam" || squadUnitView !== "personalities") {
      setSquadViewMode(view);
    }
  }
  if (!isProbeOpen()) syncDocumentSeo();
}

/**
 * Show one tool. Probe (Single / Compare) is a HAS Rank detail modal.
 */
function setTool(tool: AppTool) {
  if (isProbeOpen()) closeProbe({ restoreHash: false });
  activeTool = tool;
  persistActiveTool(tool);
  syncToolView();
}

function syncPanelChrome() {
  const savesPanel = history.panel === "saves";
  historyHeadingEl.hidden = !savesPanel;
  historyHeadingEl.textContent = "Saves";
  historyBackEl.hidden = savesPanel;
  historyNewEl.hidden = !savesPanel;
  historyNewPlayerEl.hidden = savesPanel;
  historyPlayerSortEl.hidden = savesPanel;
  historyEmptyEl.textContent = savesPanel
    ? "No saves yet."
    : "No players in this save yet.";
  saveFormEl.hidden = !savesPanel;
  playerLabelFormEl.hidden = savesPanel;
  setLabelFormEnabled();
  syncDeleteControl();
  syncPlayerSortControls();
  syncToolView();
}

function syncDeleteControl() {
  if (history.panel === "saves") {
    const save = findSave(history, history.activeSaveId);
    const enabled = Boolean(save);
    historyDeleteEl.disabled = !enabled;
    historyDeleteEl.title = enabled ? "Delete save" : "Select a save to delete";
    historyDeleteEl.setAttribute(
      "aria-label",
      enabled ? "Delete save" : "Delete save (none selected)",
    );
    return;
  }
  const player = findPlayer(history, history.activeSaveId, history.activePlayerId);
  const enabled = Boolean(player);
  historyDeleteEl.disabled = !enabled;
  historyDeleteEl.title = enabled ? "Delete player" : "Select a player to delete";
  historyDeleteEl.setAttribute(
    "aria-label",
    enabled ? "Delete player" : "Delete player (none selected)",
  );
}

function scrollActiveHistoryIntoView() {
  const active = historyListEl.querySelector<HTMLElement>(".card-main.active");
  active?.scrollIntoView({ block: "nearest" });
}

historyListEl.addEventListener("scroll", hideMetricTip, { passive: true });

function openSave(saveId: string) {
  commitActiveCardBeforeSwitch();
  const save = findSave(history, saveId);
  if (!save) return;
  history.activeSaveId = save.id;
  history.activePlayerId = save.players[0]?.id ?? null;
  history.panel = "players";
  activeTool = "roster";
  const player = findPlayer(history, save.id, history.activePlayerId);
  fillPlayerForm(player ?? null);
  if (player) {
    applySignals(player);
    runEstimate();
  } else {
    setDefaults();
    clearResults();
  }
  renderHistory();
  void persistHistory();
}

function renderHistory() {
  historyListEl.replaceChildren();
  syncPanelChrome();
  const save = findSave(history, history.activeSaveId);
  const entries =
    history.panel === "saves"
      ? orderedItems(history.saves)
      : orderedPlayers(save?.players ?? []);
  historyEmptyEl.hidden = entries.length > 0;

  for (const entry of entries) {
    const item = document.createElement("li");

    const card = document.createElement("div");
    card.className = "card-main";
    card.classList.toggle(
      "active",
      entry.id ===
        (history.panel === "saves"
          ? history.activeSaveId
          : history.activePlayerId),
    );
    card.tabIndex = 0;
    card.setAttribute("role", "button");

    const top = document.createElement("div");
    top.className = "history-card-top";

    const primary = document.createElement("span");
    primary.className = "primary";
    if (history.panel === "saves") {
      const current = entry as GameSave;
      primary.textContent = current.name || "\u00a0";
      if (!current.name) primary.classList.add("is-empty");
    } else {
      const current = entry as PlayerEntry;
      const displayName = current.labels.playerName?.trim();
      const personality = current.signals.personality.trim();
      primary.textContent = displayName || personality || "\u00a0";
      primary.title = personality;
      if (!displayName && !personality) primary.classList.add("is-empty");
      const pos = current.labels.position?.trim();
      const uid = current.labels.playerId?.trim();
      if (pos || uid) {
        const meta = document.createElement("span");
        meta.className = "history-card-pos";
        meta.textContent = [pos, uid].filter(Boolean).join(" · ");
        primary.append(document.createTextNode(" "), meta);
      }
    }

    top.append(primary);
    if (history.panel === "players") {
      const current = entry as PlayerEntry;
      const metrics = document.createElement("div");
      metrics.className = "history-card-metrics";
      metrics.append(
        mentalMetric(
          "ha-index",
          "Hidden attributes score",
          haScoreFromSnapshot(current.snapshot),
        ),
        mentalMetric(
          "determination",
          "Determination",
          current.signals.determination,
        ),
        mentalMetric("leadership", "Leadership", current.signals.leadership),
      );
      top.append(metrics);
    }

    const media = document.createElement("div");
    media.className = "history-card-media";
    if (history.panel === "saves") {
      const current = entry as GameSave;
      const details = [current.gameVersion, current.database].filter(Boolean);
      media.textContent =
        details.join(" · ") ||
        `${current.players.length} player${current.players.length === 1 ? "" : "s"}`;
      if (details.length) {
        media.textContent += ` · ${current.players.length} player${current.players.length === 1 ? "" : "s"}`;
      }
    } else {
      const mediaHandling = (entry as PlayerEntry).signals.mediaHandling.trim();
      media.textContent = mediaHandling || "\u00a0";
      if (!mediaHandling) media.classList.add("is-empty");
    }

    card.append(top, media);

    const meta = document.createElement("div");
    meta.className = "meta-line";
    const created = document.createElement("span");
    created.textContent = formatStamp(entry.createdAt);
    meta.append(created);
    if (wasEdited(entry) && entry.editedAt) {
      const edited = document.createElement("span");
      edited.className = "edited";
      edited.textContent = formatStamp(entry.editedAt);
      meta.append(edited);
    }
    if ("error" in entry && entry.error) {
      created.textContent = `${created.textContent} · error`;
    }
    card.append(meta);

    const activate = () => {
      if (history.panel === "saves") {
        openSave(entry.id);
        return;
      }
      if (entry.id === history.activePlayerId && activeTool === "roster") return;
      commitActiveCardBeforeSwitch();
      history.activePlayerId = entry.id;
      activeTool = "roster";
      const player = entry as PlayerEntry;
      fillPlayerForm(player);
      applySignals(player);
      renderHistory();
      void persistHistory();
      runEstimate();
    };
    card.addEventListener("click", activate);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        activate();
      }
    });

    item.append(card);
    historyListEl.append(item);
  }

  scrollActiveHistoryIntoView();
}

function syncHistoryPathLabel() {
  const pathEl = document.querySelector<HTMLElement>(".history-path");
  if (!pathEl) return;
  pathEl.innerHTML = useHistoryApi
    ? 'Saved to <code>data/history.json</code>'
    : "Saved in this browser (local storage)";
}

function readHistoryFromLocalStorage(): HistoryStore {
  try {
    const raw = window.localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) return emptyHistoryStore();
    const { store } = normalizeHistoryStore(JSON.parse(raw) as unknown);
    return store;
  } catch {
    return emptyHistoryStore();
  }
}

function writeHistoryToLocalStorage(store: HistoryStore) {
  window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(store));
}

async function loadHistory() {
  syncHistoryPathLabel();
  if (!useHistoryApi) {
    history = readHistoryFromLocalStorage();
    renderHistory();
    return;
  }
  const response = await fetch("/api/history");
  if (!response.ok) throw new Error("Failed to load history");
  const { store } = normalizeHistoryStore(await response.json());
  history = store;
  renderHistory();
}

/** Pull the edit form into the active entry before any disk write. */
function commitLabelFormToActive() {
  if (suppressLabelSync) return;
  const now = new Date().toISOString();
  if (history.panel === "saves") {
    const save = findSave(history, history.activeSaveId);
    if (!save || labelGameSaveEl.disabled) return;
    const value = readSaveForm();
    if (
      save.name === value.name &&
      save.gameVersion === value.gameVersion &&
      save.database === value.database
    ) {
      return;
    }
    save.name = value.name;
    if (value.gameVersion) save.gameVersion = value.gameVersion;
    else delete save.gameVersion;
    if (value.database) save.database = value.database;
    else delete save.database;
    save.editedAt = now;
    save.updatedAt = now;
    setLabelHeading(save.name.trim() || formatStamp(save.createdAt));
    return;
  }

  const player = findPlayer(
    history,
    history.activeSaveId,
    history.activePlayerId,
  );
  if (!player || labelPlayerNameEl.disabled) return;
  const labels = readPlayerLabels();
  if (JSON.stringify(player.labels) === JSON.stringify(labels)) return;
  player.labels = labels;
  player.editedAt = now;
  player.updatedAt = now;
  setLabelHeading(playerEditHeading(player));
  const save = findSave(history, history.activeSaveId);
  if (save) save.updatedAt = now;
}

let persistChain: Promise<void> = Promise.resolve();
let persistDirty = false;
let historyReady = false;

async function writeHistoryToDisk(options?: { allowEmpty?: boolean }) {
  if (!historyReady) return;
  commitLabelFormToActive();
  if (!useHistoryApi) {
    try {
      writeHistoryToLocalStorage(history);
    } catch {
      throw new Error("Failed to save history to browser storage");
    }
    return;
  }
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (options?.allowEmpty) headers["x-fmt-allow-empty"] = "1";
  const response = await fetch("/api/history", {
    method: "PUT",
    headers,
    body: JSON.stringify(history),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { error?: string }
      | null;
    throw new Error(body?.error ?? "Failed to save history");
  }
}

function persistHistory(options?: { allowEmpty?: boolean }): Promise<void> {
  persistDirty = true;
  const allowEmpty = Boolean(options?.allowEmpty);
  const run = persistChain.then(async () => {
    while (persistDirty) {
      persistDirty = false;
      await writeHistoryToDisk({ allowEmpty });
    }
  });
  persistChain = run.catch((error) => {
    statusEl.hidden = false;
    statusEl.textContent =
      error instanceof Error ? error.message : "History save failed";
  });
  return run;
}

function schedulePersist() {
  window.clearTimeout(saveTimer);
  saveTimer = window.setTimeout(() => {
    void persistHistory();
  }, 250);
}

/**
 * History rule: signal changes update the active entry in place.
 * New (or first input with no active) creates a card.
 */
function userHasStartedInput(): boolean {
  return (
    personalityEl.value.trim() !== "" ||
    mediaEl.value.trim() !== "" ||
    determinationEl.value.trim() !== "" ||
    leadershipEl.value.trim() !== "" ||
    ageEl.value.trim() !== "" ||
    !isRegenEl.checked
  );
}

function blankPlayer(
  signals?: Partial<HistorySignals>,
): PlayerEntry {
  const now = new Date().toISOString();
  return {
    id: newId(),
    createdAt: now,
    updatedAt: now,
    title: "New probe",
    signals: {
      personality: "",
      mediaHandling: "",
      isRegen: true,
      ...signals,
    },
    labels: {},
    caseMode: CASE_MODE,
    snapshot: {},
  };
}

function blankSave(): GameSave {
  const now = new Date().toISOString();
  return {
    id: newId(),
    createdAt: now,
    updatedAt: now,
    name: "",
    players: [],
  };
}

/** Create a history card on first input when none is selected. */
function ensureActiveHistoryEntry(): PlayerEntry | undefined {
  if (suppressHistory) return undefined;
  // Calculator is hidden on the saves overview; don't mint from deferred blur after ← Saves.
  if (history.panel === "saves") return undefined;
  let save = findSave(history, history.activeSaveId);
  if (!save) {
    if (!userHasStartedInput()) return undefined;
    save = blankSave();
    history.saves.unshift(save);
    history.activeSaveId = save.id;
    history.panel = "players";
    fillSaveForm(save);
  }
  const active = findPlayer(history, save.id, history.activePlayerId);
  if (active) return active;
  if (!userHasStartedInput()) return undefined;

  const personality = personalityEl.value.trim();
  const media = mediaEl.value.trim();
  const entry = blankPlayer({
    personality,
    mediaHandling: media,
    isRegen: isRegenEl.checked,
    ...(safeOptionalInt(determinationEl.value) !== undefined
      ? { determination: safeOptionalInt(determinationEl.value) }
      : {}),
    ...(safeOptionalInt(leadershipEl.value) !== undefined
      ? { leadership: safeOptionalInt(leadershipEl.value) }
      : {}),
    ...(safeOptionalInt(ageEl.value) !== undefined
      ? { age: safeOptionalInt(ageEl.value) }
      : {}),
  });
  entry.title =
    personality || media
      ? `${personality || "…"} / ${media || "…"}`
      : "New probe";

  save.players.unshift(entry);
  save.updatedAt = entry.updatedAt;
  history.activePlayerId = entry.id;
  history.panel = "players";
  fillPlayerForm(entry);
  renderHistory();
  schedulePersist();
  return entry;
}

function queueHistory(
  signals: HistorySignals,
  caseMode: CaseMode,
  result: EstimateResult | null,
  error?: string,
) {
  if (suppressHistory) return;
  if (history.panel === "saves") return;
  pendingHistory = { signals, caseMode, result, ...(error ? { error } : {}) };
  window.clearTimeout(historyTimer);
  historyTimer = window.setTimeout(() => {
    flushHistory();
  }, 350);
}

function flushHistory() {
  if (!pendingHistory) return;
  const { signals: nextSignals, caseMode, result, error } = pendingHistory;
  pendingHistory = undefined;

  const save = findSave(history, history.activeSaveId);
  if (!save) return;
  const latest = findPlayer(
    history,
    history.activeSaveId,
    history.activePlayerId,
  );
  const now = new Date().toISOString();
  const snapshot = result ? snapshotFrom(result) : {};
  const title = `${nextSignals.personality} / ${nextSignals.mediaHandling}`;

  if (latest && !forceCreateNext) {
    if (
      signalsEqual(latest.signals, nextSignals) &&
      latest.caseMode === caseMode &&
      (error ?? undefined) === latest.error
    ) {
      return;
    }

    latest.signals = nextSignals;
    latest.caseMode = caseMode;
    latest.updatedAt = now;
    latest.title = title;
    latest.snapshot = snapshot;
    if (error) latest.error = error;
    else delete latest.error;
    save.updatedAt = now;

    renderHistory();
    schedulePersist();
    return;
  }

  // Don't mint while browsing saves (e.g. race after ← Saves cleared activePlayerId).
  if (history.panel === "saves") return;

  forceCreateNext = false;
  const entry: PlayerEntry = {
    id: newId(),
    createdAt: now,
    updatedAt: now,
    title,
    signals: nextSignals,
    labels: {},
    caseMode,
    snapshot,
    ...(error ? { error } : {}),
  };

  save.players.unshift(entry);
  save.updatedAt = now;
  history.activePlayerId = entry.id;
  renderHistory();
  fillPlayerForm(entry);
  schedulePersist();
}

function createNewSave() {
  commitActiveCardBeforeSwitch();
  const save = blankSave();
  history.saves.unshift(save);
  history.activeSaveId = save.id;
  history.activePlayerId = null;
  history.panel = "saves";
  activeTool = "rank";
  forceCreateNext = false;
  renderHistory();
  fillSaveForm(save);
  void persistHistory();
  labelGameSaveEl.focus();
}

function createNewPlayer() {
  commitActiveCardBeforeSwitch();
  const save = findSave(history, history.activeSaveId);
  if (!save) {
    createNewSave();
    openSave(history.activeSaveId!);
    return;
  }
  const entry = blankPlayer();
  save.players.unshift(entry);
  save.updatedAt = entry.updatedAt;
  history.activePlayerId = entry.id;
  history.panel = "players";
  activeTool = "roster";
  forceCreateNext = false;
  suppressHistory = true;
  personalityEl.value = "";
  mediaEl.value = "";
  determinationEl.value = "";
  leadershipEl.value = "";
  ageEl.value = "";
  isRegenEl.checked = true;
  syncRegenChip(isRegenEl);
  suppressHistory = false;

  clearResults();
  clearFieldWarnings();
  renderHistory();
  fillPlayerForm(entry);
  void persistHistory();
}

function syncActiveCardFromForm(personality: string, media: string) {
  if (suppressHistory) return;
  const active = findPlayer(
    history,
    history.activeSaveId,
    history.activePlayerId,
  );
  if (!active) return;

  active.signals = {
    personality,
    mediaHandling: media,
    isRegen: isRegenEl.checked,
    ...(safeOptionalInt(determinationEl.value) !== undefined
      ? { determination: safeOptionalInt(determinationEl.value) }
      : {}),
    ...(safeOptionalInt(leadershipEl.value) !== undefined
      ? { leadership: safeOptionalInt(leadershipEl.value) }
      : {}),
    ...(safeOptionalInt(ageEl.value) !== undefined
      ? { age: safeOptionalInt(ageEl.value) }
      : {}),
  };
  active.title =
    personality || media
      ? `${personality || "…"} / ${media || "…"}`
      : "New probe";
  active.updatedAt = new Date().toISOString();
  delete active.error;
  const save = findSave(history, history.activeSaveId);
  if (save) save.updatedAt = active.updatedAt;
  renderHistory();
  schedulePersist();
}

function runEstimate() {
  syncQuickPicks();
  ensureActiveHistoryEntry();

  const personality = personalityEl.value.trim();
  const media = mediaEl.value.trim();
  const personalityKnown = Boolean(findPersonality(catalog, personality));
  const mediaResolved = media
    ? (normalizeMatch(media, mediaStyles) ?? undefined)
    : undefined;
  const canEstimate = personalityKnown || Boolean(mediaResolved);

  if (!canEstimate) {
    clearResults();
    showFieldWarnings(collectFieldViolations());
    syncActiveCardFromForm(personality, media);
    return;
  }

  try {
    const base = readSignals();
    const signals = {
      isRegen: base.isRegen,
      ...(personalityKnown ? { personality: base.personality } : {}),
      ...(mediaResolved ? { mediaHandling: mediaResolved } : {}),
      ...(base.determination !== undefined
        ? { determination: base.determination }
        : {}),
      ...(base.leadership !== undefined ? { leadership: base.leadership } : {}),
      ...(base.age !== undefined ? { age: base.age } : {}),
    };
    const result = estimatePlayer(catalog, signals);
    lastImpliedVisible = result.impliedVisible;

    if (!enforcePass && enforceVisibleInputs(result.impliedVisible)) {
      enforcePass = true;
      runEstimate();
      enforcePass = false;
      return;
    }

    statusEl.hidden = true;
    statusEl.textContent = "";
    renderResult(result);
    syncQuickPicks();
    queueHistory(
      {
        personality: base.personality,
        mediaHandling: base.mediaHandling,
        isRegen: base.isRegen,
        ...(base.determination !== undefined
          ? { determination: base.determination }
          : {}),
        ...(base.leadership !== undefined ? { leadership: base.leadership } : {}),
        ...(base.age !== undefined ? { age: base.age } : {}),
      },
      CASE_MODE,
      result,
    );
  } catch (error) {
    renderEmptyAttributeRows();
    showFieldWarnings(collectFieldViolations());
    syncActiveCardFromForm(personality, media);
    const message =
      error instanceof Error ? error.message : "Unknown estimation error";
    statusEl.hidden = false;
    statusEl.textContent = message;
  }
}

function setDefaults() {
  personalityEl.value = "";
  mediaEl.value = "";
  determinationEl.value = "";
  leadershipEl.value = "";
  ageEl.value = "";
  setIsRegen(isRegenEl, true);
  syncQuickPicks();
}

function selectedCheckPersonality(): PersonalityDefinition | undefined {
  const raw = checkPersonalityEl.value.trim();
  if (!raw) return undefined;
  return findPersonality(catalog, raw);
}

function selectedCheckMedia(): MediaHandlingDefinition | undefined {
  const raw = checkMediaEl.value.trim();
  if (!raw) return undefined;
  try {
    const styles = parseMediaHandlingInput(raw);
    return findMediaHandling(catalog, styles);
  } catch {
    return undefined;
  }
}

function isVisibleAttribute(
  attribute: string,
): attribute is VisibleAttribute {
  return (VISIBLE_ATTRIBUTES as readonly string[]).includes(attribute);
}

function renderEmptyCheckAttributeRows() {
  checkAttrBodyEl.replaceChildren();
  resetCheckVisibleAttrRow("determination");
  resetCheckVisibleAttrRow("leadership");
  for (const attribute of CHECKER_TABLE_ATTRIBUTES) {
    const row = document.createElement("tr");
    row.classList.add("is-empty");
    row.dataset.attribute = attribute;
    if (isVisibleAttribute(attribute)) {
      row.classList.add("is-visible-attr");
    }
    row.innerHTML = `
      <td>
        <span class="attr-name" title="${ATTRIBUTE_DESCRIPTIONS[attribute]}">
          ${ATTRIBUTE_LABELS[attribute]}
        </span>
      </td>
      <td class="attr-band fmt-band is-empty">—</td>
      <td class="attr-mid fmt-mid is-empty">—</td>
    `;
    checkAttrBodyEl.append(row);
  }
}

function clearCheckResults() {
  lastCheckEstimateResult = null;
  renderEmptyCheckAttributeRows();
  renderCheckRadar(null);
  renderCheckComboCard(null);
  checkStatusEl.hidden = true;
  checkStatusEl.textContent = "";
  lastCheckImpliedVisible = {};
  syncCheckViewChrome();
  syncQuickPicks();
}

function checkPlotMid(
  attribute: (typeof CHECKER_TABLE_ATTRIBUTES)[number],
  result: EstimateResult,
): number | null {
  if (isVisibleAttribute(attribute)) {
    return checkVisibleBand(attribute, result)?.midpoint ?? null;
  }
  const estimate = result.attributes[attribute];
  if (
    !estimate ||
    estimate.unmodeled ||
    estimate.impossible ||
    estimate.min > estimate.max
  ) {
    return null;
  }
  return estimate.midpoint;
}

function syncCheckViewChrome() {
  for (const btn of checkViewModeEl.querySelectorAll<HTMLButtonElement>(
    ".check-view-btn",
  )) {
    const active = btn.dataset.checkView === checkViewMode;
    btn.setAttribute("aria-pressed", String(active));
  }
  const showPlot = checkViewMode === "plot";
  checkTableWrapEl.hidden = showPlot;
  checkRadarWrapEl.hidden = !showPlot;
}

function renderCheckRadar(result: EstimateResult | null) {
  const size = 620;
  const cx = size / 2;
  const cy = size / 2;
  // Leave a clear rim for mid readouts + attribute labels.
  const radius = 128;
  const valueRing = radius + 24;
  const labelRing = radius + 52;
  const n = CHECKER_TABLE_ATTRIBUTES.length;
  const color = COMPARE_RADAR_COLORS[0]!;
  checkRadarEl.replaceChildren();

  const rings = svgEl("g", { class: "check-radar-rings" });
  for (const level of [5, 10, 15, 20]) {
    const pts = CHECKER_TABLE_ATTRIBUTES.map((_, i) => {
      const p = radarPoint(i, n, level, cx, cy, radius);
      return `${p.x.toFixed(1)},${p.y.toFixed(1)}`;
    }).join(" ");
    rings.append(
      svgEl("polygon", {
        class: "check-radar-grid",
        points: pts,
      }),
    );
  }
  checkRadarEl.append(rings);

  const axes = svgEl("g", { class: "check-radar-axes" });
  CHECKER_TABLE_ATTRIBUTES.forEach((attribute, i) => {
    const tip = radarPoint(i, n, 20, cx, cy, radius);
    axes.append(
      svgEl("line", {
        class: "check-radar-axis",
        x1: cx,
        y1: cy,
        x2: tip.x.toFixed(1),
        y2: tip.y.toFixed(1),
      }),
    );
    const labelAngle = -Math.PI / 2 + (i / n) * Math.PI * 2;
    const cos = Math.cos(labelAngle);
    const sin = Math.sin(labelAngle);
    const anchor =
      cos > 0.35 ? "start" : cos < -0.35 ? "end" : "middle";
    const lx = cx + cos * labelRing;
    const ly = cy + sin * labelRing;
    const label = svgEl("text", {
      class: "check-radar-label",
      x: lx.toFixed(1),
      y: ly.toFixed(1),
      dy: "0.35em",
      "text-anchor": anchor,
    });
    label.textContent = ATTRIBUTE_LABELS[attribute];
    axes.append(label);
  });
  checkRadarEl.append(axes);

  if (!result) return;

  // Skip unknown mids so the polygon chords across gaps instead of
  // collapsing missing spokes into the centre.
  const known: {
    index: number;
    attribute: (typeof CHECKER_TABLE_ATTRIBUTES)[number];
    value: number;
    rawMid: number;
  }[] = [];
  CHECKER_TABLE_ATTRIBUTES.forEach((attribute, index) => {
    const mid = checkPlotMid(attribute, result);
    if (mid === null) return;
    known.push({
      index,
      attribute,
      value: radarPlotValue(attribute, mid),
      rawMid: mid,
    });
  });
  if (known.length === 0) return;

  const series = svgEl("g", { class: "check-radar-series" });
  if (known.length >= 3) {
    const pts = known
      .map(({ index, value }) => {
        const p = radarPoint(index, n, value, cx, cy, radius);
        return `${p.x.toFixed(1)},${p.y.toFixed(1)}`;
      })
      .join(" ");
    series.append(
      svgEl("polygon", {
        class: "check-radar-poly",
        points: pts,
        fill: color.fill,
        stroke: color.stroke,
      }),
    );
  } else if (known.length === 2) {
    const a = radarPoint(known[0]!.index, n, known[0]!.value, cx, cy, radius);
    const b = radarPoint(known[1]!.index, n, known[1]!.value, cx, cy, radius);
    series.append(
      svgEl("line", {
        class: "check-radar-poly",
        x1: a.x.toFixed(1),
        y1: a.y.toFixed(1),
        x2: b.x.toFixed(1),
        y2: b.y.toFixed(1),
        stroke: color.stroke,
        fill: "none",
      }),
    );
  }
  for (const { index, attribute, value, rawMid } of known) {
    const p = radarPoint(index, n, value, cx, cy, radius);
    series.append(
      svgEl("circle", {
        class: "check-radar-dot",
        cx: p.x.toFixed(1),
        cy: p.y.toFixed(1),
        r: 3.2,
        fill: color.stroke,
      }),
    );
    // Fixed halo outside the web — clear of the polygon and of rim names.
    const angle = -Math.PI / 2 + (index / n) * Math.PI * 2;
    const tone = attributeTone(attribute, rawMid);
    const label = svgEl("text", {
      class: ["check-radar-value", tone === "neutral" ? "" : tone]
        .filter(Boolean)
        .join(" "),
      x: (cx + Math.cos(angle) * valueRing).toFixed(1),
      y: (cy + Math.sin(angle) * valueRing).toFixed(1),
      dy: "0.35em",
    });
    label.textContent = Number.isInteger(rawMid)
      ? String(rawMid)
      : rawMid.toFixed(1);
    series.append(label);
  }
  checkRadarEl.append(series);
}

function sortCombosByHas(entries: ComboRankEntry[]): ComboRankEntry[] {
  return [...entries].sort(
    (a, b) =>
      b.haScore - a.haScore ||
      b.floorScore - a.floorScore ||
      a.personality.localeCompare(b.personality) ||
      a.mediaHandling.localeCompare(b.mediaHandling) ||
      String(a.label ?? "").localeCompare(String(b.label ?? "")),
  );
}

/** HAS ladder for Checker carousel (worse ← current → better). */
function checkerHasLadder(): ComboRankEntry[] {
  if (lastRankerEntries.length === 0) {
    renderPersonalityRanker();
  }
  const isRegen = checkIsRegenEl.checked;
  const filtered = lastRankerEntries.filter((entry) => {
    if (entry.label === "NEWGEN") return isRegen;
    if (entry.label === "REAL") return !isRegen;
    return true;
  });
  if (filtered.length > 0) return sortCombosByHas(filtered);
  return sortCombosByHas(
    rankPersonalityMediaCombos(catalog, { isRegen }).entries,
  );
}

/**
 * Custom card neighbors: nearest by HAS, but left must be rank ≥ n+1 and
 * right rank ≤ n−1 (n = live insertion rank). Ends of the board hide a side.
 */
function findCustomHasNeighbors(
  liveHas: number,
  liveRank: number,
  ladder: ComboRankEntry[],
  currentPersonality?: string,
  currentMedia?: string,
): { worse: ComboRankEntry | null; better: ComboRankEntry | null } {
  let better: ComboRankEntry | null = null;
  let worse: ComboRankEntry | null = null;
  const person = currentPersonality?.trim();
  const media = currentMedia?.trim();

  for (const entry of ladder) {
    if (
      person &&
      media &&
      entry.personality === person &&
      entry.mediaHandling === media
    ) {
      continue;
    }
    if (entry.haScore > liveHas + 1e-9) {
      if (entry.rank <= liveRank - 1) better = entry;
      continue;
    }
    if (entry.haScore < liveHas - 1e-9) {
      if (entry.rank >= liveRank + 1) {
        worse = entry;
        break;
      }
    }
  }
  return { worse, better };
}

/** Catalog rank adjacency on the HAS ladder (index 0 = #1). */
function findRankAdjacentNeighbors(
  entry: ComboRankEntry,
  ladder: ComboRankEntry[],
): { worse: ComboRankEntry | null; better: ComboRankEntry | null } {
  let index = ladder.findIndex(
    (row) =>
      row.personality === entry.personality &&
      row.mediaHandling === entry.mediaHandling &&
      (row.label ?? null) === (entry.label ?? null),
  );
  if (index < 0) {
    index = ladder.findIndex(
      (row) =>
        row.personality === entry.personality &&
        row.mediaHandling === entry.mediaHandling,
    );
  }
  if (index < 0) return { worse: null, better: null };
  return {
    better: ladder[index - 1] ?? null,
    worse: ladder[index + 1] ?? null,
  };
}

/** 1 + count of ladder rows with a strictly higher catalog HAS. */
function liveHasInsertionRank(
  liveHas: number,
  ladder: ComboRankEntry[],
): number {
  let better = 0;
  for (const entry of ladder) {
    if (entry.haScore > liveHas + 1e-9) better += 1;
    else break;
  }
  return better + 1;
}

function knownMidMatchesCatalog(
  filled: number | undefined,
  catalogMid: number | null | undefined,
): boolean {
  if (catalogMid == null || !Number.isFinite(catalogMid)) {
    return filled === undefined;
  }
  if (filled === undefined) return false;
  return Math.round(catalogMid) === filled;
}

/** True when Checker Det/Lea still match this ranked combo’s catalog mids. */
function checkerKnownAttrsMatchCatalog(entry: ComboRankEntry): boolean {
  return (
    knownMidMatchesCatalog(
      safeOptionalInt(checkDeterminationEl.value),
      entry.mids.determination,
    ) &&
    knownMidMatchesCatalog(
      safeOptionalInt(checkLeadershipEl.value),
      entry.mids.leadership,
    )
  );
}

function setKnownMidInput(
  input: HTMLInputElement,
  value: number | null | undefined,
) {
  if (value == null || !Number.isFinite(value)) {
    input.value = "";
    return;
  }
  input.value = String(Math.round(value));
}

/**
 * Prefill probe from a ranked combo (Det/Lea mids) and optionally open the modal.
 */
function applyCheckerCombo(
  entry: ComboRankEntry,
  options?: { navigate?: boolean },
) {
  checkPersonalityEl.value = entry.personality;
  checkMediaEl.value = entry.mediaHandling;
  if (entry.label === "NEWGEN") setIsRegen(checkIsRegenEl, true);
  else if (entry.label === "REAL") setIsRegen(checkIsRegenEl, false);

  setKnownMidInput(checkDeterminationEl, entry.mids.determination);
  setKnownMidInput(checkLeadershipEl, entry.mids.leadership);

  lastCheckerSyncedComboKey = checkerComboKey(
    entry.personality,
    entry.mediaHandling,
    checkIsRegenEl.checked,
  );

  const personality = findPersonality(catalog, entry.personality);
  if (personality) {
    applyPersonalityPrerequisites(personality, {
      ageEl: checkAgeEl,
      isRegenEl: checkIsRegenEl,
      determinationEl: checkDeterminationEl,
      leadershipEl: checkLeadershipEl,
    });
  }

  syncQuickPicks();
  if (options?.navigate) {
    openProbe({ mode: "single" });
    return;
  }
  runCheckEstimate();
}

function syncCarouselArrow(
  arrow: HTMLButtonElement,
  enabled: boolean,
  label: string,
) {
  arrow.disabled = !enabled;
  arrow.setAttribute("aria-label", label);
  if (enabled) arrow.removeAttribute("aria-hidden");
  else arrow.setAttribute("aria-hidden", "true");
}

function fillCarouselSide(
  el: HTMLButtonElement,
  entry: ComboRankEntry | null,
  directionLabel: string,
) {
  el.replaceChildren();
  el.classList.remove("has-combo", "is-good", "is-bad");
  delete el.dataset.personality;
  delete el.dataset.media;
  delete el.dataset.label;
  const arrow =
    el.dataset.side === "worse"
      ? checkCarouselArrowWorseEl
      : checkCarouselArrowBetterEl;
  if (!entry) {
    el.classList.add("is-empty");
    el.disabled = true;
    el.setAttribute("aria-hidden", "true");
    el.removeAttribute("title");
    el.setAttribute("aria-label", directionLabel);
    syncCarouselArrow(arrow, false, directionLabel);
    return;
  }

  el.classList.remove("is-empty");
  el.disabled = false;
  el.setAttribute("aria-hidden", "false");
  el.classList.add("has-combo");
  if (entry.tone === "good") el.classList.add("is-good");
  if (entry.tone === "bad") el.classList.add("is-bad");
  el.dataset.personality = entry.personality;
  el.dataset.media = entry.mediaHandling;
  if (entry.label) el.dataset.label = entry.label;

  const place = document.createElement("span");
  place.className = "ranker-place";
  if (entry.tone === "good") place.classList.add("is-good");
  if (entry.tone === "bad") place.classList.add("is-bad");
  place.textContent = `#${entry.rank}`;

  const name = document.createElement("p");
  name.className = "ranker-combo-name";
  name.textContent = entry.personality;

  const media = document.createElement("p");
  media.className = "ranker-combo-media";
  media.textContent = entry.mediaHandling;

  const meta = document.createElement("div");
  meta.className = "ranker-podium-meta";
  meta.append(createHaBadge(entry.haScore, entry.tone));

  el.append(place, name, media, meta);
  setPodiumPopulationLabel(el, entry.label);
  el.title = `${directionLabel}: ${rankerEntryTitle(entry)}`;
  el.setAttribute(
    "aria-label",
    `${directionLabel}: ${entry.personality}, ${entry.mediaHandling}, #${entry.rank}`,
  );
  syncCarouselArrow(
    arrow,
    true,
    `${directionLabel}: ${entry.personality}, ${entry.mediaHandling}`,
  );
}

function renderCheckCarousel(options?: {
  liveHas?: number;
  liveRank?: number;
  personality?: string;
  media?: string;
  /** When set, neighbors are #n±1 on the Rank ladder (ranked card). */
  rankedEntry?: ComboRankEntry | null;
} | null) {
  if (
    !options ||
    options.liveHas === undefined ||
    !Number.isFinite(options.liveHas)
  ) {
    fillCarouselSide(checkComboWorseEl, null, "Slightly worse combo");
    fillCarouselSide(checkComboBetterEl, null, "Slightly better combo");
    return;
  }
  const ladder = checkerHasLadder();
  let worse: ComboRankEntry | null = null;
  let better: ComboRankEntry | null = null;

  if (options.rankedEntry) {
    ({ worse, better } = findRankAdjacentNeighbors(
      options.rankedEntry,
      ladder,
    ));
  } else if (
    options.liveRank !== undefined &&
    Number.isFinite(options.liveRank)
  ) {
    const person =
      findPersonality(catalog, options.personality?.trim() ?? "")?.id ??
      options.personality?.trim();
    let media = options.media?.trim();
    if (media) {
      try {
        const resolved = findMediaHandling(
          catalog,
          parseMediaHandlingInput(media),
        );
        if (resolved) media = formatMediaHandlingLabel(resolved.styles);
      } catch {
        // keep typed media label
      }
    }
    ({ worse, better } = findCustomHasNeighbors(
      options.liveHas,
      options.liveRank,
      ladder,
      person,
      media,
    ));
  }

  fillCarouselSide(checkComboWorseEl, worse, "Slightly worse combo");
  fillCarouselSide(checkComboBetterEl, better, "Slightly better combo");
}

function resolveCarouselEntry(
  el: HTMLButtonElement,
): ComboRankEntry | undefined {
  const personality = el.dataset.personality;
  const media = el.dataset.media;
  if (!personality || !media) return undefined;
  const label = el.dataset.label as ComboRankEntry["label"] | undefined;
  return (
    checkerHasLadder().find(
      (entry) =>
        entry.personality === personality &&
        entry.mediaHandling === media &&
        (label ? entry.label === label : !entry.label),
    ) ??
    checkerHasLadder().find(
      (entry) =>
        entry.personality === personality && entry.mediaHandling === media,
    )
  );
}

function bindCheckCarousel() {
  const onSide = (el: HTMLButtonElement) => {
    el.addEventListener("click", () => {
      const entry = resolveCarouselEntry(el);
      if (entry) applyCheckerCombo(entry);
    });
  };
  onSide(checkComboWorseEl);
  onSide(checkComboBetterEl);

  checkCarouselArrowWorseEl.addEventListener("click", () => {
    if (!checkComboWorseEl.disabled) checkComboWorseEl.click();
  });
  checkCarouselArrowBetterEl.addEventListener("click", () => {
    if (!checkComboBetterEl.disabled) checkComboBetterEl.click();
  });
}

function renderCheckComboCard(
  result: EstimateResult | null,
  options?: { rank?: number; visible?: HaVisibleKnown },
) {
  const midRankClasses = ["is-mid-gold", "is-mid-silver", "is-mid-bronze"] as const;

  if (!result) {
    checkComboCardEl.removeAttribute("title");
    checkComboCardEl.classList.remove("has-combo", "is-good", "is-bad");
    checkComboRankEl.textContent = "#000";
    checkComboRankEl.classList.remove(
      "is-good",
      "is-bad",
      ...midRankClasses,
    );
    checkComboRankEl.classList.add("is-placeholder");
    checkComboPersonalityEl.textContent = "Hidden attributes";
    checkComboMediaEl.textContent = "Pick a personality to estimate bands";
    checkComboMetaEl.replaceChildren();
    renderCheckCarousel(null);
    return;
  }

  const personality =
    result.player.personality?.trim() ||
    checkPersonalityEl.value.trim() ||
    "—";
  const media =
    result.player.mediaHandling?.trim() ||
    checkMediaEl.value.trim() ||
    "";
  const score = hiddenQualityScore(result.attributes, options?.visible);
  const finite = Number.isFinite(score);
  const tone = finite
    ? hiddenQualityTone(score, catalogEliteHasFloor, catalogPoorHasCeiling)
    : "neutral";

  const ladder = finite ? checkerHasLadder() : [];
  const catalogEntry = findCheckerRankEntry(
    personality,
    media,
    checkIsRegenEl.checked,
  );
  const catalogMatch = Boolean(
    catalogEntry && checkerKnownAttrsMatchCatalog(catalogEntry),
  );
  const liveRank = finite ? liveHasInsertionRank(score, ladder) : undefined;
  const displayRank = catalogMatch
    ? catalogEntry!.rank
    : (liveRank ?? options?.rank);
  const isGenerated = finite && !catalogMatch && displayRank !== undefined;
  const midHas =
    catalogEntry && Number.isFinite(catalogEntry.haScore)
      ? catalogEntry.haScore
      : undefined;
  /** Custom #rank medals vs this combo’s mid HAS; catalog mids → silver. */
  const midMedal: "gold" | "silver" | "bronze" | undefined = !finite
    ? undefined
    : catalogMatch
      ? "silver"
      : midHas !== undefined
        ? score > midHas + 1e-9
          ? "gold"
          : score < midHas - 1e-9
            ? "bronze"
            : "silver"
        : isGenerated
          ? "silver"
          : undefined;

  checkComboCardEl.classList.add("has-combo");
  checkComboCardEl.classList.toggle("is-good", tone === "good");
  checkComboCardEl.classList.toggle("is-bad", tone === "bad");

  checkComboRankEl.classList.remove(
    "is-good",
    "is-bad",
    ...midRankClasses,
  );
  if (displayRank !== undefined) {
    checkComboRankEl.textContent = `#${displayRank}`;
    checkComboRankEl.classList.remove("is-placeholder");
    if (midMedal === "gold") {
      checkComboRankEl.classList.add("is-mid-gold");
    } else if (midMedal === "bronze") {
      checkComboRankEl.classList.add("is-mid-bronze");
    } else if (midMedal === "silver") {
      checkComboRankEl.classList.add("is-mid-silver");
    } else {
      checkComboRankEl.classList.toggle("is-good", tone === "good");
      checkComboRankEl.classList.toggle("is-bad", tone === "bad");
    }
  } else {
    checkComboRankEl.textContent = "#000";
    checkComboRankEl.classList.add("is-placeholder");
  }

  checkComboPersonalityEl.textContent = personality;
  checkComboMediaEl.textContent = media || "—";

  checkComboMetaEl.replaceChildren();
  if (finite) {
    checkComboMetaEl.append(createHaBadge(score, tone));
  } else {
    const empty = document.createElement("span");
    empty.className = "ranker-ha";
    empty.textContent = "—";
    checkComboMetaEl.append(empty);
  }

  const weightsTip = formatHaQualityWeightsTip(options?.visible);
  if (!finite) {
    checkComboCardEl.title =
      "HA index unavailable — personality / media bands conflict on at least one attribute";
  } else if (isGenerated && displayRank !== undefined) {
    const midTip =
      midHas !== undefined && midMedal
        ? ` · vs mid HAS ${formatHaScore(midHas)}: ${
            midMedal === "gold"
              ? "above (gold)"
              : midMedal === "bronze"
                ? "below (bronze)"
                : "equal (silver)"
          }`
        : "";
    checkComboCardEl.title = `Generated placement #${displayRank} from live HAS ${formatHaScore(score)}${midTip} (Det/Lea differ from the Rank table row) · elite ≥ ${formatHaScore(catalogEliteHasFloor)} · poor ≤ ${formatHaScore(catalogPoorHasCeiling)} · ${weightsTip}`;
  } else if (displayRank !== undefined) {
    checkComboCardEl.title = `Combo rank #${displayRank} · elite ≥ ${formatHaScore(catalogEliteHasFloor)} · poor ≤ ${formatHaScore(catalogPoorHasCeiling)} · ${weightsTip}`;
  } else {
    checkComboCardEl.title = `Elite ≥ ${formatHaScore(catalogEliteHasFloor)} · poor ≤ ${formatHaScore(catalogPoorHasCeiling)} · ${weightsTip}`;
  }

  renderCheckCarousel(
    finite
      ? {
          liveHas: score,
          liveRank: displayRank,
          personality,
          media,
          rankedEntry: catalogMatch ? catalogEntry : null,
        }
      : null,
  );
}

function checkVisibleBand(
  attribute: VisibleAttribute,
  result: EstimateResult,
): {
  min: number;
  max: number;
  midpoint: number;
  exact: boolean;
  entered: boolean;
  impliedMid: number | undefined;
} | null {
  const entered =
    attribute === "determination"
      ? result.player.determination
      : result.player.leadership;
  const implied = result.impliedVisible[attribute];
  const impliedMid = implied ? (implied.min + implied.max) / 2 : undefined;

  if (entered !== undefined) {
    return {
      min: entered,
      max: entered,
      midpoint: entered,
      exact: true,
      entered: true,
      impliedMid,
    };
  }
  if (!implied) return null;
  return {
    min: implied.min,
    max: implied.max,
    midpoint: impliedMid!,
    exact: implied.min === implied.max,
    entered: false,
    impliedMid,
  };
}

function resetCheckVisibleAttrRow(attribute: VisibleAttribute) {
  const attrEl = attribute === "determination" ? checkDetAttrEl : checkLeaAttrEl;
  attrEl.classList.remove("good", "bad", "exact");
  attrEl.removeAttribute("title");
}

function updateCheckVisibleAttrRow(
  attribute: VisibleAttribute,
  result: EstimateResult | null,
) {
  const attrEl = attribute === "determination" ? checkDetAttrEl : checkLeaAttrEl;

  if (!result) {
    resetCheckVisibleAttrRow(attribute);
    return;
  }

  const band = checkVisibleBand(attribute, result);
  attrEl.classList.remove("good", "bad", "exact");

  if (!band) {
    attrEl.title = "Not constrained by this personality / media combo";
    return;
  }

  const tone = attributeTone(attribute, band.midpoint);
  if (tone !== "neutral") attrEl.classList.add(tone);
  if (band.exact) attrEl.classList.add("exact");

  if (band.entered && band.impliedMid !== undefined) {
    const delta = band.midpoint - band.impliedMid;
    const vs =
      Math.abs(delta) < 1e-9
        ? "at combo mid"
        : delta > 0
          ? `above combo mid ${formatHaMid(band.impliedMid)}`
          : `below combo mid ${formatHaMid(band.impliedMid)}`;
    attrEl.title = `Entered ${band.midpoint} · ${vs}`;
  } else if (band.entered) {
    attrEl.title = `Entered ${band.midpoint}`;
  } else {
    attrEl.title = `Implied by personality / media · mid ${formatHaMid(band.midpoint)}`;
  }
}

function appendCheckVisibleTableRow(
  attribute: VisibleAttribute,
  result: EstimateResult,
) {
  const band = checkVisibleBand(attribute, result);
  const row = document.createElement("tr");
  row.dataset.attribute = attribute;
  row.classList.add("is-visible-attr");

  if (!band) {
    row.classList.add("is-empty");
    row.innerHTML = `
      <td>
        <span class="attr-name" title="${ATTRIBUTE_DESCRIPTIONS[attribute]}">
          ${ATTRIBUTE_LABELS[attribute]}
        </span>
      </td>
      <td class="attr-band fmt-band is-empty">—</td>
      <td class="attr-mid fmt-mid is-empty">—</td>
    `;
    row.title = "Not constrained by this personality / media combo";
    checkAttrBodyEl.append(row);
    return;
  }

  // Manual Det/Lea overwrites the HA table band to an exact value (same as
  // the chip-side range). Mid follows the entered value.
  const tone = attributeTone(attribute, band.midpoint);
  const mid = Number.isInteger(band.midpoint)
    ? String(band.midpoint)
    : band.midpoint.toFixed(1);
  const range = formatBandSpan({ min: band.min, max: band.max });
  const toneClass = tone === "neutral" ? "" : tone;
  const exactClass = band.exact ? "exact" : "";

  row.innerHTML = `
    <td>
      <span class="attr-name" title="${ATTRIBUTE_DESCRIPTIONS[attribute]}">
        ${ATTRIBUTE_LABELS[attribute]}
      </span>
    </td>
    <td class="attr-band fmt-band ${exactClass} ${toneClass}">${range}</td>
    <td class="attr-mid fmt-mid ${toneClass}">${mid}</td>
  `;

  if (band.entered && band.impliedMid !== undefined) {
    const delta = band.midpoint - band.impliedMid;
    const vs =
      Math.abs(delta) < 1e-9
        ? "at combo mid"
        : delta > 0
          ? `above combo mid ${formatHaMid(band.impliedMid)}`
          : `below combo mid ${formatHaMid(band.impliedMid)}`;
    const implied = result.impliedVisible[attribute];
    row.title = implied
      ? `Implied ${formatBandSpan(implied)} · entered ${band.midpoint} (${vs})`
      : `Entered ${band.midpoint} (${vs})`;
  } else if (band.entered) {
    row.title = `Entered ${band.midpoint}`;
  } else {
    row.title = `Implied by personality / media · mid ${mid}`;
  }

  checkAttrBodyEl.append(row);
}

function renderCheckResult(result: EstimateResult) {
  lastCheckEstimateResult = result;
  checkAttrBodyEl.replaceChildren();

  for (const attribute of VISIBLE_ATTRIBUTES) {
    updateCheckVisibleAttrRow(attribute, result);
  }

  for (const attribute of CHECKER_TABLE_ATTRIBUTES) {
    if (isVisibleAttribute(attribute)) {
      appendCheckVisibleTableRow(attribute, result);
      continue;
    }

    const estimate = result.attributes[attribute];
    const unmodeled =
      Boolean(estimate.unmodeled) || isUnmodeledHiddenAttribute(attribute);
    const impossible = Boolean(
      !unmodeled && (estimate.impossible || estimate.min > estimate.max),
    );
    const tone = unmodeled
      ? "neutral"
      : impossible
        ? "bad"
        : attributeTone(attribute, estimate.midpoint);
    const row = document.createElement("tr");
    row.dataset.attribute = attribute;
    if (impossible) row.classList.add("is-impossible");
    if (unmodeled) row.classList.add("is-unmodeled");
    const mid =
      unmodeled || impossible
        ? "—"
        : Number.isInteger(estimate.midpoint)
          ? String(estimate.midpoint)
          : estimate.midpoint.toFixed(1);
    const range =
      unmodeled || impossible
        ? "—"
        : formatBandSpan({ min: estimate.min, max: estimate.max });
    const toneClass =
      mid === "—" ? "is-empty" : tone === "neutral" ? "" : tone;
    const exactClass = estimate.exact && !unmodeled ? "exact" : "";

    row.innerHTML = `
      <td>
        <span class="attr-name" title="${ATTRIBUTE_DESCRIPTIONS[attribute]}">
          ${ATTRIBUTE_LABELS[attribute]}
        </span>
      </td>
      <td class="attr-band fmt-band ${exactClass} ${toneClass}">${range}</td>
      <td class="attr-mid fmt-mid ${toneClass}">${mid}</td>
    `;
    if (unmodeled) {
      row.title = ATTRIBUTE_DESCRIPTIONS[attribute];
    } else if (impossible) {
      row.title =
        "Empty intersection (min > max) — this personality / media combo likely does not exist in-game";
    }
    checkAttrBodyEl.append(row);
  }

  renderCheckRadar(result);
  syncCheckViewChrome();

  renderCheckComboCard(result, {
    rank: lookupComboRank(
      result.player.personality,
      result.player.mediaHandling,
      Boolean(result.player.isRegen),
    ),
    visible: visibleKnownFromEstimate(result),
  });
}

function collectCheckFieldViolations(): FieldViolation[] {
  const violations: FieldViolation[] = [];
  const personality = selectedCheckPersonality();
  const media = selectedCheckMedia();
  if (personality) {
    const block = personalityBlockReason(
      personality,
      checkIsRegenEl.checked,
      safeOptionalInt(checkAgeEl.value),
    );
    if (block) violations.push(block);
    const listConflict = personalityListViolation(
      personality,
      safeOptionalInt(checkAgeEl.value),
      media,
      safeOptionalInt(checkDeterminationEl.value),
      safeOptionalInt(checkLeadershipEl.value),
    );
    if (listConflict && listConflict.violation.field !== "mediaHandling") {
      violations.push(listConflict.violation);
    }
  }
  if (personality && media && !isPersonalityMediaCompatible(personality, media)) {
    const conflict = comboConflictViolation(
      personality,
      media,
      "mediaHandling",
    );
    violations.push(conflict);
    violations.push({ ...conflict, field: "personality" });
  }
  return violations;
}

function runCheckEstimate() {
  syncQuickPicks();
  persistCheckerDraft();

  const personality = checkPersonalityEl.value.trim();
  const media = checkMediaEl.value.trim();
  const personalityKnown = Boolean(findPersonality(catalog, personality));
  const mediaResolved = media
    ? (normalizeMatch(media, mediaStyles) ?? undefined)
    : undefined;
  const canEstimate = personalityKnown || Boolean(mediaResolved);

  if (!canEstimate) {
    clearCheckResults();
    showFieldWarnings(collectCheckFieldViolations());
    return;
  }

  try {
    const determination = parseOptionalInt(checkDeterminationEl.value);
    const leadership = parseOptionalInt(checkLeadershipEl.value);
    const age = parseOptionalInt(checkAgeEl.value);
    assertAttrInScale("Determination", determination);
    assertAttrInScale("Leadership", leadership);

    const personalityMatch = findPersonality(catalog, checkPersonalityEl.value);
    const signals = {
      isRegen: checkIsRegenEl.checked,
      ...(personalityKnown
        ? { personality: personalityMatch?.id ?? personality }
        : {}),
      ...(mediaResolved ? { mediaHandling: mediaResolved } : {}),
      ...(determination !== undefined ? { determination } : {}),
      ...(leadership !== undefined ? { leadership } : {}),
      ...(age !== undefined ? { age } : {}),
    };
    const result = estimatePlayer(catalog, signals);
    lastCheckImpliedVisible = result.impliedVisible;
    checkStatusEl.hidden = true;
    checkStatusEl.textContent = "";
    renderCheckResult(result);
    showFieldWarnings(collectCheckFieldViolations());
    syncQuickPicks();
  } catch (error) {
    clearCheckResults();
    showFieldWarnings(collectCheckFieldViolations());
    const message =
      error instanceof Error ? error.message : "Unknown estimation error";
    checkStatusEl.hidden = false;
    checkStatusEl.textContent = message;
  }
}

bindCombo(personalityEl, personalityListEl, () => personalityComboOptions(), {
  onCommit: runEstimate,
  isPersonality: true,
  siblingInput: mediaEl,
  siblingList: mediaListEl,
  getIsRegen: () => isRegenEl.checked,
  getAge: () => safeOptionalInt(ageEl.value),
  getSelectedMedia: selectedMedia,
  getSelectedPersonality: selectedPersonality,
  getDetermination: () => safeOptionalInt(determinationEl.value),
  getLeadership: () => safeOptionalInt(leadershipEl.value),
  personalityFields: {
    ageEl,
    isRegenEl,
    determinationEl,
    leadershipEl,
  },
});

bindRegenChip(isRegenEl, isRegenChipEl);
bindRegenChip(checkIsRegenEl, checkIsRegenChipEl);
bindCombo(mediaEl, mediaListEl, () => mediaComboOptions(), {
  onCommit: runEstimate,
  isPersonality: false,
  siblingInput: personalityEl,
  siblingList: personalityListEl,
  getIsRegen: () => isRegenEl.checked,
  getAge: () => safeOptionalInt(ageEl.value),
  getSelectedMedia: selectedMedia,
  getSelectedPersonality: selectedPersonality,
  getDetermination: () => safeOptionalInt(determinationEl.value),
  getLeadership: () => safeOptionalInt(leadershipEl.value),
  personalityFields: {
    ageEl,
    isRegenEl,
    determinationEl,
    leadershipEl,
  },
});

bindCombo(
  checkPersonalityEl,
  checkPersonalityListEl,
  () =>
    personalityComboOptions(
      checkIsRegenEl.checked,
      safeOptionalInt(checkAgeEl.value),
      selectedCheckMedia(),
      safeOptionalInt(checkDeterminationEl.value),
      safeOptionalInt(checkLeadershipEl.value),
    ),
  {
    onCommit: commitCheckPersonalityOrMedia,
    isPersonality: true,
    siblingInput: checkMediaEl,
    siblingList: checkMediaListEl,
    getIsRegen: () => checkIsRegenEl.checked,
    getAge: () => safeOptionalInt(checkAgeEl.value),
    getSelectedMedia: selectedCheckMedia,
    getSelectedPersonality: selectedCheckPersonality,
    getDetermination: () => safeOptionalInt(checkDeterminationEl.value),
    getLeadership: () => safeOptionalInt(checkLeadershipEl.value),
    personalityFields: {
      ageEl: checkAgeEl,
      isRegenEl: checkIsRegenEl,
      determinationEl: checkDeterminationEl,
      leadershipEl: checkLeadershipEl,
    },
  },
);
bindCombo(
  checkMediaEl,
  checkMediaListEl,
  () => mediaComboOptions(selectedCheckPersonality()),
  {
    onCommit: commitCheckPersonalityOrMedia,
    isPersonality: false,
    siblingInput: checkPersonalityEl,
    siblingList: checkPersonalityListEl,
    getIsRegen: () => checkIsRegenEl.checked,
    getAge: () => safeOptionalInt(checkAgeEl.value),
    getSelectedMedia: selectedCheckMedia,
    getSelectedPersonality: selectedCheckPersonality,
    getDetermination: () => safeOptionalInt(checkDeterminationEl.value),
    getLeadership: () => safeOptionalInt(checkLeadershipEl.value),
    personalityFields: {
      ageEl: checkAgeEl,
      isRegenEl: checkIsRegenEl,
      determinationEl: checkDeterminationEl,
      leadershipEl: checkLeadershipEl,
    },
  },
);

for (const group of document.querySelectorAll<HTMLElement>(".quick-picks")) {
  const target = group.dataset.target;
  if (!target) continue;
  const form = group.closest("form");
  const input =
    form?.querySelector<HTMLInputElement>(`#${target}`) ??
    document.querySelector<HTMLInputElement>(`#${target}`);
  if (!input) continue;

  // Don't steal focus from an open personality/media combo — dismiss+lock first
  // via the capture pointerdown handler, then apply the pick without reopening.
  group.addEventListener("mousedown", (event) => {
    const button = (event.target as HTMLElement).closest("button");
    if (!button || !group.contains(button)) return;
    event.preventDefault();
  });

  group.addEventListener("click", (event) => {
    const button = (event.target as HTMLElement).closest("button");
    if (!button || !group.contains(button)) return;
    closeAndLockOpenCombos();
    input.value = button.dataset.value ?? "";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    // Checker Age/Det/Lea popovers are :focus-within — blur closes them after a pick.
    if (group.classList.contains("check-focus-picks")) {
      input.blur();
    }
  });
}

for (const el of [
  determinationEl,
  leadershipEl,
  isRegenEl,
  ageEl,
]) {
  el.addEventListener("input", () => {
    if (!personalityListEl.hidden || !mediaListEl.hidden) {
      closeAndLockOpenCombos();
    }
    runEstimate();
  });
  el.addEventListener("change", runEstimate);
}

for (const el of [
  checkDeterminationEl,
  checkLeadershipEl,
  checkIsRegenEl,
  checkAgeEl,
]) {
  el.addEventListener("input", () => {
    if (!checkPersonalityListEl.hidden || !checkMediaListEl.hidden) {
      closeAndLockOpenCombos();
    }
    if (el === checkIsRegenEl) {
      syncCheckerKnownAttrsFromComboIfChanged();
    }
    runCheckEstimate();
  });
  el.addEventListener("change", () => {
    if (el === checkIsRegenEl) {
      syncCheckerKnownAttrsFromComboIfChanged();
    }
    runCheckEstimate();
  });
}

bindCheckCarousel();

historyToggleEl.addEventListener("click", () => {
  const open = shellEl.dataset.historyOpen !== "true";
  shellEl.dataset.historyOpen = open ? "true" : "false";
  historyToggleEl.setAttribute("aria-expanded", String(open));
  historyToggleEl.setAttribute(
    "aria-label",
    open ? "Collapse history" : "Expand history",
  );
  historyToggleEl.title = open ? "Collapse history" : "Expand history";
});

historyNewEl.addEventListener("click", () => {
  createNewSave();
});

historyNewPlayerEl.addEventListener("click", () => {
  createNewPlayer();
});

historySortByEl.addEventListener("change", () => {
  const value = historySortByEl.value as PlayerSortKey;
  const allowed: PlayerSortKey[] = [
    "createdAt",
    "updatedAt",
    "ha",
    "determination",
    "leadership",
    "professionalism",
    "ambition",
    "pressure",
    "temperament",
    "loyalty",
    "sportsmanship",
    "controversy",
  ];
  if (!allowed.includes(value)) return;
  playerSortKey = value;
  renderHistory();
});

historySortDirEl.addEventListener("click", () => {
  playerSortAsc = !playerSortAsc;
  syncPlayerSortControls();
  renderHistory();
});

historyBackEl.addEventListener("click", () => {
  commitActiveCardBeforeSwitch();
  history.panel = "saves";
  history.activePlayerId = null;
  fillSaveForm(findSave(history, history.activeSaveId) ?? null);
  renderHistory();
  void persistHistory();
});

function deleteActivePlayer() {
  const save = findSave(history, history.activeSaveId);
  const player = findPlayer(history, history.activeSaveId, history.activePlayerId);
  if (!save || !player) return;

  const label =
    player.labels.playerName?.trim() ||
    player.signals.personality.trim() ||
    "this player";
  if (!window.confirm(`Delete ${label}?`)) return;

  const index = save.players.findIndex((entry) => entry.id === player.id);
  save.players = save.players.filter((entry) => entry.id !== player.id);
  save.updatedAt = new Date().toISOString();

  const next =
    save.players[index] ??
    save.players[index - 1] ??
    save.players[0] ??
    null;
  history.activePlayerId = next?.id ?? null;
  fillPlayerForm(next);
  if (next) {
    applySignals(next);
    runEstimate();
  } else {
    setDefaults();
    clearResults();
  }
  renderHistory();
  void persistHistory({ allowEmpty: playerCount(history) === 0 });
}

function deleteActiveSave() {
  const save = findSave(history, history.activeSaveId);
  if (!save) return;

  const label = save.name.trim() || "this save";
  const count = save.players.length;
  const playersLabel =
    count === 0
      ? "no players"
      : `${count} player${count === 1 ? "" : "s"}`;
  if (!window.confirm(`Delete ${label} and ${playersLabel}?`)) return;

  const index = history.saves.findIndex((entry) => entry.id === save.id);
  history.saves = history.saves.filter((entry) => entry.id !== save.id);
  const next = history.saves[index] ?? history.saves[index - 1] ?? history.saves[0] ?? null;
  history.activeSaveId = next?.id ?? null;
  history.activePlayerId = null;
  fillSaveForm(next);
  fillPlayerForm(null);
  setDefaults();
  clearResults();
  renderHistory();
  void persistHistory({ allowEmpty: playerCount(history) === 0 });
}

historyDeleteEl.addEventListener("click", () => {
  if (history.panel === "saves") deleteActiveSave();
  else deleteActivePlayer();
});

fillLabelSelects();
fillSaveForm(null);
fillPlayerForm(null);
renderEmptyAttributeRows();
clearCheckResults();

function scheduleLabelPersist() {
  const hasTarget =
    history.panel === "saves"
      ? Boolean(findSave(history, history.activeSaveId))
      : Boolean(
          findPlayer(history, history.activeSaveId, history.activePlayerId),
        );
  if (suppressLabelSync || !hasTarget) return;
  window.clearTimeout(labelSaveTimer);
  labelSaveTimer = window.setTimeout(() => {
    commitLabelFormToActive();
    renderHistory();
    schedulePersist();
  }, 300);
}

labelDatabaseEl.addEventListener("change", () => {
  syncCustomDatabaseVisibility();
  scheduleLabelPersist();
});

function applySaveMetaProbe(probe: SaveMetaProbe) {
  if (probe.gameVersion) {
    const known = (FM_GAME_VERSIONS as readonly string[]).includes(
      probe.gameVersion,
    );
    if (known) labelGameVersionEl.value = probe.gameVersion;
  }

  if (probe.database) {
    if ((FM_DATABASE_VERSIONS as readonly string[]).includes(probe.database)) {
      labelDatabaseEl.value = probe.database;
      labelDatabaseCustomEl.value = "";
    } else {
      labelDatabaseEl.value = CUSTOM_DATABASE_VALUE;
      labelDatabaseCustomEl.value = probe.database;
    }
    syncCustomDatabaseVisibility();
  }
}

labelBrowseSaveEl.addEventListener("click", () => {
  labelSaveFileEl.click();
});

labelSaveFileEl.addEventListener("change", () => {
  const file = labelSaveFileEl.files?.[0];
  if (!file) return;
  // Strip extension for a readable save label; keep path loading for later.
  labelGameSaveEl.value = file.name.replace(/\.[^.]+$/, "");
  void probeSaveFile(file).then((probe) => {
    applySaveMetaProbe(probe);
    scheduleLabelPersist();
  });
  scheduleLabelPersist();
});

labelBrowseDatabaseEl.addEventListener("click", () => {
  labelDatabaseFileEl.click();
});

labelDatabaseFileEl.addEventListener("change", () => {
  const file = labelDatabaseFileEl.files?.[0];
  if (!file) return;
  labelDatabaseCustomEl.value = file.name.replace(/\.[^.]+$/, "");
  scheduleLabelPersist();
});

labelDatabaseClearEl.addEventListener("click", () => {
  labelDatabaseEl.value = "";
  labelDatabaseCustomEl.value = "";
  labelDatabaseFileEl.value = "";
  syncCustomDatabaseVisibility();
  scheduleLabelPersist();
});

for (const el of [
  labelGameVersionEl,
  labelDatabaseCustomEl,
  labelGameSaveEl,
  labelPlayerIdEl,
  labelPlayerNameEl,
  labelPlayerPositionEl,
]) {
  el.addEventListener("input", () => scheduleLabelPersist());
  el.addEventListener("change", () => scheduleLabelPersist());
}

saveFormEl.addEventListener("submit", (event) => {
  event.preventDefault();
});

playerLabelFormEl.addEventListener("submit", (event) => {
  event.preventDefault();
});

window.addEventListener("beforeunload", () => {
  if (!historyReady) return;
  window.clearTimeout(saveTimer);
  window.clearTimeout(labelSaveTimer);
  window.clearTimeout(historyTimer);
  if (pendingHistory) flushHistory();
  commitLabelFormToActive();
  try {
    if (!useHistoryApi) {
      writeHistoryToLocalStorage(history);
      return;
    }
    void fetch("/api/history", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(history),
      keepalive: true,
    });
  } catch {
    // best-effort flush on unload
  }
});

void loadHistory()
  .then(() => {
    historyReady = true;
    const save = findSave(history, history.activeSaveId);
    const player = findPlayer(
      history,
      history.activeSaveId,
      history.activePlayerId,
    );
    fillSaveForm(save ?? null);
    fillPlayerForm(player ?? null);
    restoreCheckerDraft();
    const stored = readStoredTool();
    activeTool =
      stored ??
      (history.panel === "players" && player ? "roster" : "rank");
    // Stay on Squad when the URL asks for it — empty state is the upload CTA,
    // not a bounce to Rank (that looked like Career Saves were wiped).
    const hashWantsRoster = readHashRoute().tool === "roster";
    if (
      activeTool === "roster" &&
      rosterSaveCount() === 0 &&
      !hashWantsRoster
    ) {
      activeTool = "rank";
    }
    persistActiveTool(activeTool);
    applyActiveRosterFromStore();
    syncToolView();
    if (pendingOpenProbe) {
      const mode = pendingOpenProbeMode;
      pendingOpenProbe = false;
      pendingOpenProbeMode = "single";
      openProbe({ mode });
    }
  })
  .catch((error) => {
    historyReady = true;
    statusEl.hidden = false;
    statusEl.textContent =
      error instanceof Error ? error.message : "Failed to load history";
    fillSaveForm(null);
    fillPlayerForm(null);
    restoreCheckerDraft();
    activeTool = readStoredTool() ?? "rank";
    const hashWantsRoster = readHashRoute().tool === "roster";
    if (
      activeTool === "roster" &&
      rosterSaveCount() === 0 &&
      !hashWantsRoster
    ) {
      activeTool = "rank";
    }
    persistActiveTool(activeTool);
    applyActiveRosterFromStore();
    syncToolView();
    if (pendingOpenProbe) {
      const mode = pendingOpenProbeMode;
      pendingOpenProbe = false;
      pendingOpenProbeMode = "single";
      openProbe({ mode });
    }
  });

appBrandEl.addEventListener("click", () => {
  closeProbe({ restoreHash: false });
  setTool("rank");
});

toolNavEl.addEventListener("click", (event) => {
  const btn = (event.target as HTMLElement).closest<HTMLButtonElement>(
    "[data-tool]",
  );
  if (!btn || !toolNavEl.contains(btn) || btn.disabled) return;
  const tool = btn.dataset.tool;
  if (tool === "rank" || tool === "roster") {
    setTool(tool);
  }
});

checkerCloseEl.addEventListener("click", () => {
  closeProbe();
});

checkerDialogEl.addEventListener("close", () => {
  if (!suppressProbeHashRestore) {
    const hash = readHashToolRaw();
    if (hash === "checker" || hash === "compare") syncProbeHash(false);
  }
  syncDocumentSeo();
});

probeModeEl.addEventListener("click", (event) => {
  const btn = (event.target as HTMLElement).closest<HTMLButtonElement>(
    "[data-probe-mode]",
  );
  if (!btn || !probeModeEl.contains(btn)) return;
  const mode = btn.dataset.probeMode;
  if (!isProbeMode(mode) || mode === probeMode) return;
  setProbeMode(mode);
});

syncRankerModeButtons();
renderPersonalityRanker();
ensureCompareSlots();
applyActiveRosterFromStore();
startSaveAutoSync();
syncToolView();
syncProbeModeChrome();
// Probe from #checker / #compare / legacy pages opens after history draft restore.
