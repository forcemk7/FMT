"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ShellHeader, type Screen } from "@/components/shell-header";
import { MyTeamScreen } from "@/components/my-team-screen";
import { LaterRoleScreen } from "@/components/later-role-screen";
import { PlayerProfileScreen } from "@/components/player-profile-screen";
import { SettingsScreen } from "@/components/settings-screen";
import { ClubProfileScreen } from "@/components/club-profile-screen";
import { DashboardScreen, DashboardViewScreen } from "@/components/dashboard-screen";
import { TooltipProvider } from "@/components/ui/tooltip";
import {
  fm26LiveAdapter,
  type LiveConnectorStatus,
  type LiveFootballSnapshot,
  type LivePlayer,
} from "@/domain/adapters";
import { recordPlayersFromSnapshot } from "@/domain/attribute-history";
import { isDashViewId, type DashViewId } from "@/domain/dashboard-views";
import { toggleFavorite, type FavoriteRecord } from "@/domain/live-data";
import { warmSquadGraphics } from "@/domain/warm-squad-graphics";
import { applyAttrColorPalette, loadAttrColorPalette } from "@/domain/attr-colors";

const initialStatus: LiveConnectorStatus = {
  processDetected: false,
  processId: null,
  processPath: null,
  saveDetected: null,
  memoryAccess: "not_checked",
  parserStatus: "unverified",
  state: "not_checked",
  playersLoaded: 0,
  managedSquadPlayers: 0,
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
  pointerValidation: "not_run",
  handleAccessFlags: "Not checked",
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
  message: "Diagnostics have not run yet.",
  warnings: [],
};

const initialSnapshot: LiveFootballSnapshot = {
  status: initialStatus,
  managedClubId: null,
  managerName: null,
  season: null,
  clubs: [],
  players: [],
  tactic: null,
  tacticSource: "none",
  dataError: null,
  dataSource: "none",
  dataWarnings: [],
};

const LATER_ROLES: Screen[] = [
  "Tactic",
  "HoYD",
  "General Manager",
  "Loan Manager",
  "Technical Director",
];

export function FMTApp() {
  const [screen, setScreenState] = useState<Screen>("Dashboard");
  const [screenHistory, setScreenHistory] = useState<Screen[]>(["Dashboard"]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const [search, setSearch] = useState("");
  const [snapshot, setSnapshot] = useState<LiveFootballSnapshot>(initialSnapshot);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);
  const [selectedClubId, setSelectedClubId] = useState<string | null>(null);
  const [returnScreen, setReturnScreen] = useState<Screen>("Dashboard");
  const [favorites, setFavorites] = useState<FavoriteRecord[]>(() => {
    if (typeof window === "undefined") return [];
    const stored =
      window.localStorage.getItem("fmt-favorites-v1") ??
      window.localStorage.getItem("glassscout-favorites-v1");
    if (!stored) return [];
    try {
      return JSON.parse(stored) as FavoriteRecord[];
    } catch {
      window.localStorage.removeItem("fmt-favorites-v1");
      window.localStorage.removeItem("glassscout-favorites-v1");
      return [];
    }
  });
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    window.localStorage.setItem("fmt-favorites-v1", JSON.stringify(favorites));
  }, [favorites]);

  useEffect(() => {
    applyAttrColorPalette(loadAttrColorPalette());
  }, []);

  const navigate = useCallback(
    (nextScreen: Screen) => {
      if (nextScreen === screen) return;
      const nextIndex = historyIndex + 1;
      setScreenHistory((current) => [...current.slice(0, nextIndex), nextScreen]);
      setHistoryIndex(nextIndex);
      setScreenState(nextScreen);
    },
    [historyIndex, screen],
  );

  const goBack = useCallback(() => {
    if (historyIndex <= 0) return;
    const nextIndex = historyIndex - 1;
    setHistoryIndex(nextIndex);
    setScreenState(screenHistory[nextIndex]);
  }, [historyIndex, screenHistory]);

  const checkConnection = useCallback(async () => {
    setChecking(true);
    try {
      const nextSnapshot = await fm26LiveAdapter.getSnapshot();
      if (nextSnapshot.status.state === "connected" && nextSnapshot.players.length) {
        recordPlayersFromSnapshot(nextSnapshot.players, nextSnapshot.season);
        // UID → background XML index → disk cache. Never block Load Active Save.
        warmSquadGraphics(nextSnapshot);
      }
      setSnapshot(nextSnapshot);
      return nextSnapshot.status;
    } finally {
      setChecking(false);
    }
  }, []);

  const togglePlayerFavorite = (playerId: string) =>
    setFavorites((current) => toggleFavorite(current, playerId));

  const openPlayer = useCallback(
    (playerId: string) => {
      setReturnScreen((current) =>
        screen === "Player Profile" || screen === "Club Profile" ? current : screen,
      );
      setSelectedPlayerId(playerId);
      navigate("Player Profile");
    },
    [navigate, screen],
  );

  const openDashView = useCallback(
    (view: DashViewId) => {
      navigate(view);
    },
    [navigate],
  );

  const openClub = useCallback(
    (clubId: string) => {
      setReturnScreen((current) =>
        screen === "Player Profile" || screen === "Club Profile" ? current : screen,
      );
      setSelectedClubId(clubId);
      navigate("Club Profile");
    },
    [navigate, screen],
  );

  const goBackOrReturn = useCallback(() => {
    if (historyIndex > 0) {
      goBack();
      return;
    }
    navigate(returnScreen);
  }, [goBack, historyIndex, navigate, returnScreen]);

  const squadSearchHits = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return [] as LivePlayer[];
    return snapshot.players.filter((player) => player.name.toLowerCase().includes(q)).slice(0, 8);
  }, [search, snapshot.players]);

  const content =
    screen === "Dashboard" ? (
      <DashboardScreen
        snapshot={snapshot}
        checking={checking}
        onRefresh={checkConnection}
        onOpenPlayer={openPlayer}
        onOpenView={openDashView}
      />
    ) : isDashViewId(screen) ? (
      <DashboardViewScreen
        view={screen}
        snapshot={snapshot}
        checking={checking}
        onRefresh={checkConnection}
        onOpenPlayer={openPlayer}
        onBack={() => navigate("Dashboard")}
      />
    ) : screen === "Squad" ? (
      <MyTeamScreen
        snapshot={snapshot}
        checking={checking}
        onRefresh={checkConnection}
        onOpenPlayer={openPlayer}
      />
    ) : LATER_ROLES.includes(screen) ? (
      <LaterRoleScreen role={screen} />
    ) : screen === "Player Profile" ? (
      <PlayerProfileScreen
        player={snapshot.players.find((player) => player.id === selectedPlayerId) ?? null}
        snapshot={snapshot}
        favorite={selectedPlayerId ? favorites.some((record) => record.playerId === selectedPlayerId) : false}
        checking={checking}
        onRefresh={checkConnection}
        onToggleFavorite={() => selectedPlayerId && togglePlayerFavorite(selectedPlayerId)}
        onBack={goBackOrReturn}
        onOpenClub={openClub}
        onOpenPlayer={openPlayer}
      />
    ) : screen === "Club Profile" ? (
      <ClubProfileScreen
        clubId={selectedClubId}
        snapshot={snapshot}
        onBack={goBackOrReturn}
        onOpenPlayer={openPlayer}
      />
    ) : (
      <SettingsScreen snapshot={snapshot} checking={checking} onRefresh={checkConnection} />
    );

  return (
    <TooltipProvider>
      <div className="app-canvas shell-single-header">
        <ShellHeader
          screen={screen}
          onNavigate={navigate}
          search={search}
          onSearch={setSearch}
          snapshot={snapshot}
          checking={checking}
          onRefresh={checkConnection}
        />
        {search ? (
          <motion.div
            className="global-search-results"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <header>
              <strong>Squad search</strong>
              <button type="button" onClick={() => setSearch("")}>
                Clear
              </button>
            </header>
            {squadSearchHits.map((player) => (
              <button
                key={player.id}
                type="button"
                onClick={() => {
                  openPlayer(player.id);
                  setSearch("");
                }}
              >
                <span>Player</span>
                <strong>{player.name}</strong>
                <small>{player.positions?.join(" / ") || "Position unknown"}</small>
              </button>
            ))}
            {!squadSearchHits.length ? <p>No squad player matches “{search}”.</p> : null}
          </motion.div>
        ) : null}
        <section className="app-main">
          <AnimatePresence mode="wait">
            <div key={screen} className="screen-slot">
              {content}
            </div>
          </AnimatePresence>
        </section>
      </div>
    </TooltipProvider>
  );
}
