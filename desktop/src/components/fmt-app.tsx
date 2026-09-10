"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ShellHeader, type Screen } from "@/components/shell-header";
import { MyTeamScreen } from "@/components/my-team-screen";
import { PlayerProfileScreen, type PlayerProfileTab } from "@/components/player-profile-screen";
import { SettingsScreen } from "@/components/settings-screen";
import { ClubProfileScreen } from "@/components/club-profile-screen";
import { DashboardScreen, DashboardViewScreen } from "@/components/dashboard-screen";
import { TooltipProvider } from "@/components/ui/tooltip";
import { attachSnapshotDeltas, deferRecordSnapshotPlayers } from "@/domain/attribute-history";
import { markFmtCosmeticsReady } from "@/domain/cosmetics-ready";
import { normalizeLiveSnapshot, fm26LiveAdapter, type LiveConnectorStatus, type LiveFootballSnapshot, type LivePlayer } from "@/domain/adapters";
import { warmSquadGraphics } from "@/domain/warm-squad-graphics";
import { isDashViewId, type DashViewId } from "@/domain/dashboard-views";
import { toggleFavorite, type FavoriteRecord } from "@/domain/live-data";
import { applyAttrColorPalette, loadAttrColorPalette } from "@/domain/attr-colors";
import {
  liveDeskHeadline,
  mirrorToTerminal,
  resetTerminalMirror,
  shellStatusLine,
} from "@/domain/fmt-terminal-log";
import { writeAppMainScrollTop } from "@/domain/squad-desk-session";
import { playerMatchesSquadSearch } from "@/domain/squad-search";

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
  diagnosticCells: [],
};

const initialSnapshot: LiveFootballSnapshot = {
  status: initialStatus,
  managedClubId: null,
  managerName: null,
  gameDate: null,
  season: null,
  clubs: [],
  clubTeams: [],
  players: [],
  tactic: null,
  tacticSource: "none",
  dataError: null,
  dataSource: "none",
  dataWarnings: [],
};

export function FMTApp() {
  const [screen, setScreenState] = useState<Screen>("Dashboard");
  const [screenHistory, setScreenHistory] = useState<Screen[]>(["Dashboard"]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const [search, setSearch] = useState("");
  const [searchHighlight, setSearchHighlight] = useState(0);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [snapshot, setSnapshot] = useState<LiveFootballSnapshot>(initialSnapshot);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);
  const [profileTab, setProfileTab] = useState<PlayerProfileTab>("attributes");
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
  const [loadStage, setLoadStage] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) return;
    let remove: (() => void) | null = null;
    void import("@tauri-apps/api/event")
      .then(({ listen }) =>
        listen<string>("fmt-load-progress", (event) => {
          setLoadStage(event.payload);
        }),
      )
      .then((unlisten) => {
        remove = unlisten;
      });
    return () => remove?.();
  }, []);

  useEffect(() => {
    if (checking) return;
    void mirrorToTerminal(shellStatusLine(snapshot, false, null));
  }, [snapshot, checking]);

  useEffect(() => {
    if (checking || snapshot.status.state === "connected") return;
    void mirrorToTerminal(liveDeskHeadline(snapshot, "Live data"));
  }, [snapshot, checking]);

  useEffect(() => {
    window.localStorage.setItem("fmt-favorites-v1", JSON.stringify(favorites));
  }, [favorites]);

  useEffect(() => {
    applyAttrColorPalette(loadAttrColorPalette());
  }, []);

  // Shared `.app-main` scroll must not leak into other screens.
  // Zero after Squad has unmounted (effect, not layout) so we don't flash Squad-to-top mid-swap.
  useEffect(() => {
    if (screen === "Squad") return;
    writeAppMainScrollTop(0);
  }, [screen]);

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
    resetTerminalMirror();
    setLoadStage("detecting_fm26");
    setChecking(true);
    try {
      const nextSnapshot = normalizeLiveSnapshot(await fm26LiveAdapter.getSnapshot());
      if (nextSnapshot.status.state === "connected" && nextSnapshot.players.length) {
        const players = attachSnapshotDeltas(nextSnapshot.players);
        setSnapshot({ ...nextSnapshot, players });
        deferRecordSnapshotPlayers(nextSnapshot.players, nextSnapshot.gameDate);
        window.requestAnimationFrame(() => {
          markFmtCosmeticsReady();
          warmSquadGraphics({ ...nextSnapshot, players });
        });
        return nextSnapshot.status;
      }
      setSnapshot(nextSnapshot);
      return nextSnapshot.status;
    } finally {
      setLoadStage(null);
      setChecking(false);
    }
  }, []);

  const togglePlayerFavorite = (playerId: string) =>
    setFavorites((current) => toggleFavorite(current, playerId));

  const openPlayer = useCallback(
    (playerId: string, options?: { tab?: PlayerProfileTab }) => {
      setReturnScreen((current) =>
        screen === "Player Profile" || screen === "Club Profile" ? current : screen,
      );
      setSelectedPlayerId(playerId);
      setProfileTab(options?.tab ?? "attributes");
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
    const q = search.trim();
    if (!q) return [] as LivePlayer[];
    return snapshot.players
      .filter((player) => playerMatchesSquadSearch(player.name, q))
      .slice(0, 12);
  }, [search, snapshot.players]);

  useEffect(() => {
    setSearchHighlight(0);
  }, [search]);

  const clearSearch = useCallback(() => {
    setSearch("");
    setSearchHighlight(0);
  }, []);

  const openSearchHit = useCallback(
    (playerId: string) => {
      openPlayer(playerId);
      clearSearch();
    },
    [openPlayer, clearSearch],
  );

  useEffect(() => {
    const connected = snapshot.status.state === "connected";
    const onKey = (event: KeyboardEvent) => {
      const findChord =
        (event.key === "f" || event.key === "F") && (event.ctrlKey || event.metaKey);
      if (findChord && connected) {
        event.preventDefault();
        const input = searchInputRef.current;
        if (input) {
          input.focus();
          input.select();
        }
        return;
      }

      if (!search.trim()) return;

      if (event.key === "Escape") {
        event.preventDefault();
        clearSearch();
        searchInputRef.current?.blur();
        return;
      }

      const active = document.activeElement;
      const searchFocused = active === searchInputRef.current;
      const inResults = active?.closest?.(".global-search-results") != null;
      if (!searchFocused && !inResults) {
        const tag = (active as HTMLElement | null)?.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      }

      if (event.key === "ArrowDown" && squadSearchHits.length) {
        event.preventDefault();
        setSearchHighlight((index) => Math.min(index + 1, squadSearchHits.length - 1));
        return;
      }
      if (event.key === "ArrowUp" && squadSearchHits.length) {
        event.preventDefault();
        setSearchHighlight((index) => Math.max(index - 1, 0));
        return;
      }
      if (event.key === "Enter" && squadSearchHits.length && (searchFocused || inResults)) {
        event.preventDefault();
        const hit = squadSearchHits[searchHighlight] ?? squadSearchHits[0];
        if (hit) openSearchHit(hit.id);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [
    snapshot.status.state,
    search,
    squadSearchHits,
    searchHighlight,
    clearSearch,
    openSearchHit,
  ]);

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
        onBack={goBack}
      />
    ) : screen === "Squad" ? (
      <MyTeamScreen
        snapshot={snapshot}
        checking={checking}
        onRefresh={checkConnection}
        onOpenPlayer={openPlayer}
      />
    ) : screen === "Loan Manager" ? (
      <MyTeamScreen
        mode="loaned-out"
        snapshot={snapshot}
        checking={checking}
        onRefresh={checkConnection}
        onOpenPlayer={openPlayer}
      />
    ) : screen === "General Manager" ? (
      <MyTeamScreen
        mode="move-on"
        snapshot={snapshot}
        checking={checking}
        onRefresh={checkConnection}
        onOpenPlayer={openPlayer}
      />
    ) : screen === "HoYD" ? (
      <MyTeamScreen
        mode="hoyd"
        snapshot={snapshot}
        checking={checking}
        onRefresh={checkConnection}
        onOpenPlayer={openPlayer}
      />
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
        initialTab={profileTab}
      />
    ) : screen === "Club Profile" ? (
      <ClubProfileScreen
        clubId={selectedClubId}
        snapshot={snapshot}
        onBack={goBackOrReturn}
        onOpenPlayer={openPlayer}
      />
    ) : (
      <SettingsScreen snapshot={snapshot} />
    );

  return (
    <TooltipProvider>
      <div className="app-canvas shell-single-header">
        <ShellHeader
          screen={screen}
          onNavigate={navigate}
          search={search}
          onSearch={setSearch}
          searchInputRef={searchInputRef}
          snapshot={snapshot}
          checking={checking}
          loadStage={loadStage}
          onRefresh={checkConnection}
        />
        {search ? (
          <motion.div
            className="global-search-results"
            role="listbox"
            aria-label="Squad search results"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <header>
              <strong>Squad search</strong>
              <button type="button" onClick={clearSearch}>
                Clear
              </button>
            </header>
            {squadSearchHits.map((player, index) => (
              <button
                key={player.id}
                id={`squad-search-hit-${player.id}`}
                type="button"
                role="option"
                aria-selected={index === searchHighlight}
                className={index === searchHighlight ? "is-active" : undefined}
                onMouseEnter={() => setSearchHighlight(index)}
                onClick={() => openSearchHit(player.id)}
              >
                <span>Squad</span>
                <strong>{player.name}</strong>
                <small>
                  {player.positions?.length ? player.positions.join(" / ") : "Managed squad"}
                </small>
              </button>
            ))}
            {!squadSearchHits.length ? <p>No matches for “{search}”.</p> : null}
          </motion.div>
        ) : null}
        <section className="app-main">
          <div key={screen} className="screen-slot">
            {content}
          </div>
        </section>
      </div>
    </TooltipProvider>
  );
}
