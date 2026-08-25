"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AppSidebar, type Screen } from "@/components/app-sidebar";
import { Topbar } from "@/components/topbar";
import { MyTeamScreen } from "@/components/my-team-screen";
import { RoadmapScreen } from "@/components/roadmap-screen";
import { PlayerProfileScreen } from "@/components/player-profile-screen";
import { StartupScreen } from "@/components/startup-screen";
import { SettingsScreen } from "@/components/settings-screen";
import { ClubProfileScreen } from "@/components/club-profile-screen";
import { TooltipProvider } from "@/components/ui/tooltip";
import {
  fm26LiveAdapter,
  type LiveConnectorStatus,
  type LiveFootballSnapshot,
  type LivePlayer,
} from "@/domain/adapters";
import { recordPlayersFromSnapshot } from "@/domain/attribute-history";
import { toggleFavorite, type FavoriteRecord } from "@/domain/live-data";

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

export function FMTApp() {
  const [mode, setMode] = useState<"fm26" | null>(null);
  const [screen, setScreenState] = useState<Screen>("Squad");
  const [screenHistory, setScreenHistory] = useState<Screen[]>(["Squad"]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const [search, setSearch] = useState("");
  const [snapshot, setSnapshot] = useState<LiveFootballSnapshot>(initialSnapshot);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);
  const [selectedClubId, setSelectedClubId] = useState<string | null>(null);
  const [returnScreen, setReturnScreen] = useState<Screen>("Squad");
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

  const goForward = useCallback(() => {
    if (historyIndex >= screenHistory.length - 1) return;
    const nextIndex = historyIndex + 1;
    setHistoryIndex(nextIndex);
    setScreenState(screenHistory[nextIndex]);
  }, [historyIndex, screenHistory]);

  const checkConnection = useCallback(async () => {
    setChecking(true);
    try {
      const nextSnapshot = await fm26LiveAdapter.getSnapshot();
      if (nextSnapshot.status.state === "connected" && nextSnapshot.players.length) {
        recordPlayersFromSnapshot(nextSnapshot.players, nextSnapshot.season);
      }
      setSnapshot(nextSnapshot);
      return nextSnapshot.status;
    } finally {
      setChecking(false);
    }
  }, []);

  const enterWorkspace = useCallback(() => {
    setScreenState("Squad");
    setScreenHistory(["Squad"]);
    setHistoryIndex(0);
    setMode("fm26");
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

  if (mode === null) {
    return (
      <TooltipProvider>
        <StartupScreen onConnect={checkConnection} onEnter={enterWorkspace} />
      </TooltipProvider>
    );
  }

  const content =
    screen === "Squad" ? (
      <MyTeamScreen
        snapshot={snapshot}
        checking={checking}
        onRefresh={checkConnection}
        onOpenPlayer={openPlayer}
      />
    ) : screen === "Roadmap" ? (
      <RoadmapScreen />
    ) : screen === "Player Profile" ? (
      <PlayerProfileScreen
        player={snapshot.players.find((player) => player.id === selectedPlayerId) ?? null}
        snapshot={snapshot}
        favorite={selectedPlayerId ? favorites.some((record) => record.playerId === selectedPlayerId) : false}
        onToggleFavorite={() => selectedPlayerId && togglePlayerFavorite(selectedPlayerId)}
        onBack={goBackOrReturn}
        onOpenClub={openClub}
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
      <div className="app-canvas">
        <div className="app-top-shell">
          <AppSidebar screen={screen} onNavigate={navigate} />
          <Topbar
            search={search}
            onSearch={setSearch}
            snapshot={snapshot}
            screen={screen}
            checking={checking}
            onRefresh={checkConnection}
            canGoBack={historyIndex > 0}
            canGoForward={historyIndex < screenHistory.length - 1}
            onGoBack={goBack}
            onGoForward={goForward}
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
        </div>
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
