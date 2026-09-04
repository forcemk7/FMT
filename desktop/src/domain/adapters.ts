export type ConnectionState =
  | "not_checked"
  | "process_not_found"
  | "access_denied"
  | "process_ready"
  | "parser_unverified"
  | "connected";

export type LiveConnectorStatus = {
  processDetected: boolean;
  processId: number | null;
  processPath: string | null;
  saveDetected: boolean | null;
  memoryAccess: "not_checked" | "denied" | "read_only_handle_open";
  parserStatus: "unverified" | "ready" | "error";
  state: ConnectionState;
  playersLoaded: number;
  managedSquadPlayers: number;
  /** Contract-employed at managed club (index join); honesty metric before squad-unit split. */
  clubEmployees: number;
  databasePlayersIndexed: number;
  backgroundPlayersIndexed: number;
  visiblePlayersLoaded: number;
  fullyScoutedPlayers: number;
  partialScoutReports: number;
  databaseIndexStatus: "not_run" | "ready" | "partial" | "failed";
  databaseScope: "none" | "managed-squad" | "full-save-index";
  clubsLoaded: number;
  lastSync: string | null;
  bytesRead: number;
  executableHeaderValid: boolean;
  gameBuild?: string | null;
  productVersion?: string | null;
  executableSha256?: string | null;
  architecture?: string | null;
  moduleBase?: string | null;
  entityMapStatus?: "missing" | "matched" | "invalid" | "not_checked";
  entityMapProfileId?: string | null;
  mappingSchemaVersion?: number;
  mappingCoverage?: Array<{ section: string; validated: number; candidate: number; unmapped: number }>;
  pointerValidation?: "not_run" | "passed" | "failed";
  handleAccessFlags?: string;
  entityRoot?: string | null;
  savePointer?: string | null;
  managedClubPointer?: string | null;
  playerCollectionPointer?: string | null;
  liveMemoryTacticRead?: "not_run" | "object_not_found" | "object_detected_unmapped" | "ready";
  tacticManagerPointer?: string | null;
  failureStage?: string | null;
  lastSuccessfulRead?: string | null;
  windowsErrorCode?: number | null;
  readPipeline?: Array<{
    key: string;
    label: string;
    state: "passed" | "warning" | "blocked" | "pending";
    detail: string;
  }>;
  canWriteMemory: false;
  message: string;
  warnings: string[];
};

export type LivePlayer = {
  id: string;
  name: string;
  age: number | null;
  dateOfBirth?: string | null;
  nationality: string | null;
  nationalityId?: string | null;
  secondNationality?: string | null;
  positions: string[];
  /** Strong secondary slots (familiarity ≥15, below best). Shown in parentheses. */
  secondaryPositions?: string[];
  /** FM outfield desk Goalkeeper Rating (GK position familiarity, 0–10). */
  goalkeeperRating?: number | null;
  bestRole: string | null;
  playableRoles?: PlayerRoleFit[];
  otherRoles?: PlayerRoleFit[];
  currentAbility: number | null;
  potentialAbility: number | null;
  abilityScore?: number | null;
  form: string | null;
  averageRating: number | null;
  minutesPlayed: number | null;
  goals: number | null;
  assists: number | null;
  contractStatus: string | null;
  value: string | null;
  wage: string | null;
  squadImportance: string | null;
  developmentTrend: "improving" | "stable" | "declining" | null;
  tacticalFit: number | null;
  roleFit: number | null;
  preferredFoot?: string | null;
  /** Display 1–20 left-foot strength from the attribute blob */
  leftFoot?: number | null;
  /** Display 1–20 right-foot strength from the attribute blob */
  rightFoot?: number | null;
  strengths: string[];
  weaknesses: string[];
  clubId: string | null;
  clubName?: string | null;
  /** Managed-club squad unit when mapped from live read (T196). */
  squadUnit?: "firstTeam" | "under19s" | "reserves" | null;
  /** FM team object UID for the roster this player was loaded from. */
  squadTeamUid?: string | null;
  /** Highest familiarity position slot from the live 15-byte blob (single code). */
  bestCalculatedPosition?: string | null;
  /** Owned by managed club but currently out on loan (not available for match squads). */
  loanedOut?: boolean | null;
  /** On managed squad roster but employed by another club (incoming loan). */
  loanedIn?: boolean | null;
  /** Parent club when `loanedIn` (incoming loan employer). */
  employerClubId?: string | null;
  employerClubName?: string | null;
  /** Loan destination club when `loanedOut` (FMLE Loan Club). */
  loanClubId?: string | null;
  loanClubName?: string | null;
  transferInterest: string | null;
  loanInterest: string | null;
  transferAvailable: boolean | null;
  loanAvailable: boolean | null;
  notForSale?: boolean | null;
  attributes?: Record<string, number | null>;
  /** FM-hidden row: Consistency, Dirtiness, Important Matches, Injury Proneness, Versatility */
  hiddenAttributes?: Record<string, number | null>;
  /** Personality pack (Adaptability…Controversy), 1–20 when readable */
  personalityAttributes?: Record<string, number | null>;
  /** Load-history recent — Attributes desk (T188; frozen until Development solved). */
  recentAttrDeltas?: Record<string, number | null>;
  /** Development desk — Load all-time for now; replace with in-game pack when locus found. */
  allTimeAttrDeltas?: Record<string, number | null>;
  /** In-game CA pack change-points from live lookback (Development hunt). */
  caPackPointCount?: number | null;
  per90?: Record<string, number | null>;
  inPossessionFit?: number | null;
  outOfPossessionFit?: number | null;
  projectedInPossessionFit?: number | null;
  projectedOutOfPossessionFit?: number | null;
  matchSharpness?: number | null;
  fatigue?: number | null;
  efficiencyScore?: number | null;
  dossierReference?: string | null;
  scoutKnowledge?: "fully_known" | "partly_known" | "unknown" | "needs_scouting" | "missing_data";
  scoutConfidence?: number | null;
  lastScoutedDate?: string | null;
  reportReliability?: string | null;
  truePrice?: number | null;
  fairPriceRange?: [number, number] | null;
  valuationLabel?: "undervalued" | "fair" | "overpriced" | "unavailable";
  valuationReasoning?: string[];
  retrainingSuggestion?: string | null;
  roleReasoning?: string[];
  riskLevel?: "low" | "medium" | "high" | "unknown";
  marketValueAmount?: number | null;
  personality?: string | null;
  /** Coach/media handling phrase when mapped (General column). */
  mediaHandling?: string | null;
  condition?: string | null;
  heightCm?: number | null;
  rawStats?: Record<string, number | null>;
  careerTotals?: Record<string, number | null>;
  formHistory?: string | null;
  traits?: string | null;
  contractStartDate?: string | null;
  signDate?: string | null;
  contractRemaining?: string | null;
  recommendation?: RecommendationEvidence;
  knowledge?: Record<string, KnowledgeField<unknown>>;
};

export type PlayerRoleFit = {
  roleKey: string;
  role: string;
  shortRole: string;
  roleIdMask: string;
  positions: string[];
  score: number;
  positionFit: number;
  attributeFit: number | null;
  evidence: string[];
  phase?: "in-possession" | "out-of-possession" | "combined";
  inPossessionRole?: string | null;
  outOfPossessionRole?: string | null;
  inPossessionFit?: number | null;
  outOfPossessionFit?: number | null;
  redFlags?: string[];
};

export type FieldVisibility = "known" | "estimated" | "range" | "unknown";

export type KnowledgeField<T> = {
  value: T | null;
  visibility: FieldVisibility;
  source: "own-squad" | "scout-report" | "player-profile" | "data-hub" | "memory-raw";
  confidence: number;
  lastValidated: string | null;
};

export type RecommendationEvidence = {
  minimum: number | null;
  maximum: number | null;
  completeness: number;
  label: string;
};

export type LiveClub = {
  id: string;
  name: string;
  nation: string | null;
  league: string | null;
};

export type LiveTacticSlot = {
  playerId: string | null;
  position: string;
  role: string | null;
  roleShort?: string | null;
  roleMask?: string | null;
  duty: string | null;
  dutyShort?: string | null;
  dutyMask?: string | null;
  decoderStatus?: string;
};

export type LiveTactic = {
  name: string | null;
  formation: string;
  formationEnum?: string;
  slots: LiveTacticSlot[];
  teamInstructions: string[];
  playerInstructionsReadable: boolean;
  decoderStatus?: string;
  formationCode?: number;
  layoutStatus?: "exact-template" | "formation-name-only";
  roleDutyDecoderStatus?: string;
  rolePacketPointer?: string | null;
  rolePacketStride?: number | null;
  rolePacketWidth?: number | null;
  rolesResolved?: number;
  dutiesResolved?: number;
  warnings?: string[];
};

export type TacticSource = "none" | "live-memory";

export type LiveClubTeam = {
  teamUid: string;
  name: string;
  rosterLen: number;
  squadUnit: "firstTeam" | "under19s" | "reserves";
  /** Raw FM TeamType byte when known (FMScout enum). */
  teamType?: number | null;
  /** Wrapper +0x30 Affiliation Type when discovered via club+0x118. */
  affiliationType?: number | null;
  /** PGE label or `Map AffiliationType 0xNN` reminder. */
  affiliationTypeLabel?: string | null;
  isManagerTeam: boolean;
};

export function normalizeLiveSnapshot(
  snapshot: Partial<LiveFootballSnapshot> & Pick<LiveFootballSnapshot, "status">,
): LiveFootballSnapshot {
  return {
    managedClubId: snapshot.managedClubId ?? null,
    managerName: snapshot.managerName ?? null,
    gameDate: snapshot.gameDate ?? null,
    season: snapshot.season ?? null,
    clubs: snapshot.clubs ?? [],
    clubTeams: snapshot.clubTeams ?? [],
    players: snapshot.players ?? [],
    tactic: snapshot.tactic ?? null,
    tacticSource: snapshot.tacticSource ?? "none",
    dataError: snapshot.dataError ?? null,
    dataSource: snapshot.dataSource ?? "none",
    dataWarnings: snapshot.dataWarnings ?? [],
    status: snapshot.status,
  };
}

export type LiveFootballSnapshot = {
  status: LiveConnectorStatus;
  managedClubId: string | null;
  managerName: string | null;
  /** In-game calendar date (YYYY-MM-DD) used for ages; null when current-date unread. */
  gameDate: string | null;
  season: string | null;
  clubs: LiveClub[];
  clubTeams: LiveClubTeam[];
  players: LivePlayer[];
  tactic: LiveTactic | null;
  tacticSource: TacticSource;
  dataError: string | null;
  dataSource?: "none" | "live-memory";
  dataWarnings?: string[];
};

export interface FootballDataAdapter {
  readonly kind: "fm26-live";
  getStatus(): Promise<LiveConnectorStatus>;
  getSnapshot(): Promise<LiveFootballSnapshot>;
}

export interface FutureRealLifeAdapter {
  readonly kind: "real-life-future";
  readonly available: false;
  readonly providerRequired: "licensed-provider";
}

const desktopRequiredStatus: LiveConnectorStatus = {
  processDetected: false,
  processId: null,
  processPath: null,
  saveDetected: null,
  memoryAccess: "not_checked",
  parserStatus: "unverified",
  state: "parser_unverified",
  playersLoaded: 0,
  managedSquadPlayers: 0,
  clubEmployees: 0,
  databasePlayersIndexed: 0,
  backgroundPlayersIndexed: 0,
  visiblePlayersLoaded: 0,
  fullyScoutedPlayers: 0,
  partialScoutReports: 0,
  databaseIndexStatus: "not_run",
  databaseScope: "none",
  clubsLoaded: 0,
  lastSync: null,
  bytesRead: 0,
  executableHeaderValid: false,
  gameBuild: null,
  productVersion: null,
  executableSha256: null,
  architecture: null,
  moduleBase: null,
  entityMapStatus: "not_checked",
  entityMapProfileId: null,
  mappingSchemaVersion: 2,
  mappingCoverage: [],
  pointerValidation: "not_run",
  handleAccessFlags: "Not available in browser",
  entityRoot: null,
  savePointer: null,
  managedClubPointer: null,
  playerCollectionPointer: null,
  liveMemoryTacticRead: "not_run",
  tacticManagerPointer: null,
  failureStage: null,
  lastSuccessfulRead: null,
  windowsErrorCode: null,
  readPipeline: [],
  canWriteMemory: false,
  message: "FMT requires the installed Windows app to connect to the active FM26 game.",
  warnings: ["No live data is being simulated."],
};

export const fm26LiveAdapter: FootballDataAdapter = {
  kind: "fm26-live",
  async getStatus() {
    if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) {
      return desktopRequiredStatus;
    }

    try {
      const { invoke } = await import("@tauri-apps/api/core");
      return await invoke<LiveConnectorStatus>("connector_status");
    } catch (error) {
      return {
        ...desktopRequiredStatus,
        state: "access_denied",
        memoryAccess: "denied",
        message: error instanceof Error ? error.message : "The desktop connector could not be reached.",
      };
    }
  },
  async getSnapshot() {
    if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) {
      return normalizeLiveSnapshot({
        status: desktopRequiredStatus,
        managedClubId: null,
        managerName: null,
        gameDate: null,
        season: null,
        clubs: [],
        clubTeams: [],
        players: [],
        tactic: null,
        tacticSource: "none",
        dataError: desktopRequiredStatus.message,
        dataSource: "none",
        dataWarnings: desktopRequiredStatus.warnings,
      });
    }

    try {
      const { invoke } = await import("@tauri-apps/api/core");
      return normalizeLiveSnapshot(await invoke<LiveFootballSnapshot>("load_active_save"));
    } catch (error) {
      const message = error instanceof Error ? error.message : "The desktop connector could not be reached.";
      return normalizeLiveSnapshot({
        status: { ...desktopRequiredStatus, state: "access_denied", memoryAccess: "denied", message },
        managedClubId: null,
        managerName: null,
        gameDate: null,
        season: null,
        clubs: [],
        clubTeams: [],
        players: [],
        tactic: null,
        tacticSource: "none",
        dataError: message,
        dataSource: "none",
        dataWarnings: [message],
      });
    }
  },
};

export const realLifeAdapter: FutureRealLifeAdapter = {
  kind: "real-life-future",
  available: false,
  providerRequired: "licensed-provider",
};
