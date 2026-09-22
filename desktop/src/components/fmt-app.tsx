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
import { usePreferences } from "@/domain/preferences";

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
  /** Compact log shown in the load button's tooltip while checking (T274). */
  const [loadStageHistory, setLoadStageHistory] = useState<string[]>([]);
  const [switchFlash, setSwitchFlash] = useState<string | null>(null);

  // T274: auto-detect/auto-load/auto-refresh. heartbeatBaselineRef doubles as "is
  // anything currently mounted" — it's set (by checkConnection) and cleared (by the
  // poll, on a genuine not_found) in lockstep with `snapshot`, so no separate ref is
  // needed to mirror connection state. loadInFlightRef is the authoritative guard on
  // checkConnection itself — a manual Load click and a poll-triggered reload are
  // meant to be an OR (whichever gets there first wins), never an AND;
  // `checking`/`checkingRef` alone aren't enough to guarantee that, since there's a
  // real gap between the poll deciding to reload and `checking` actually flipping
  // true (the poll awaits a heartbeat first) during which the button isn't yet
  // disabled. loadInFlightRef closes that gap synchronously. (The poll's own
  // poll-vs-poll overlap guard is a plain local variable inside its effect, not a
  // ref — see the comment there for why.)
  const checkingRef = useRef(checking);
  const loadInFlightRef = useRef(false);
  const heartbeatBaselineRef = useRef<{ clubUid: number | null; gameDate: string | null } | null>(null);
  // Gates only the very first auto-load of a session (Settings > User Preferences >
  // Auto-load on startup). Once any load — manual or automatic — succeeds, this
  // flips permanently true, so disconnect/reconnect and save-switch auto-refresh
  // (T274) are never affected by this preference, only the moment FMT opens.
  const hasConnectedOnceRef = useRef(false);
  const { autoLoadOnStartup } = usePreferences();

  useEffect(() => {
    checkingRef.current = checking;
  }, [checking]);

  // Boot-sequence diagnostic marker — fires once, as early as React lets it, so the
  // terminal log shows exactly when the page actually finished mounting/hydrating
  // relative to the Rust-side boot clock (see fmt_log::mark_boot_start).
  useEffect(() => {
    void mirrorToTerminal("app: FMTApp mounted");
  }, []);

  useEffect(() => {
    if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) return;
    let remove: (() => void) | null = null;
    void import("@tauri-apps/api/event")
      .then(({ listen }) =>
        listen<string>("fmt-load-progress", (event) => {
          setLoadStageHistory((history) =>
            history[history.length - 1] === event.payload ? history : [...history, event.payload],
          );
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
    // Synchronous check-and-set, no `await` in between — the manual Load button and
    // the poll are meant to be an OR (whichever gets here first wins), never an AND.
    // A caller that loses this race (e.g. a click landing in the poll's brief
    // heartbeat-to-decision window, before `checking` has flipped true and disabled
    // the button) is a silent no-op rather than a second concurrent read.
    if (loadInFlightRef.current) return undefined;
    loadInFlightRef.current = true;

    resetTerminalMirror();
    setLoadStageHistory(["detecting_fm26"]);
    setChecking(true);
    try {
      const nextSnapshot = normalizeLiveSnapshot(await fm26LiveAdapter.getSnapshot());
      // Baseline follows the mounted snapshot in lockstep, whether this load was a
      // manual click, a poll-triggered switch, or an on-launch auto-load.
      heartbeatBaselineRef.current =
        nextSnapshot.status.state === "connected"
          ? {
              clubUid: nextSnapshot.managedClubId !== null ? Number(nextSnapshot.managedClubId) : null,
              gameDate: nextSnapshot.gameDate,
            }
          : null;
      if (nextSnapshot.status.state === "connected" && nextSnapshot.players.length) {
        hasConnectedOnceRef.current = true;
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
      setChecking(false);
      loadInFlightRef.current = false;
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) return;
    const POLL_MS = 8000;
    let cancelled = false;
    // Deliberately a local variable, not a useRef: it must reset cleanly on every
    // fresh effect instance, including React Strict Mode's dev-only mount → cleanup
    // → mount cycle. A useRef persists across that whole cycle, so the *stale* first
    // instance's still-in-flight tick (started, then cancelled before its heartbeat
    // resolved) would hold a shared ref "busy" and silently eat the *real* second
    // instance's immediate on-mount check — which is exactly why auto-load was still
    // waiting a full POLL_MS in dev even after adding the immediate `tick()` call.
    let pollBusy = false;
    // Boot-diagnostic marker, once per effect instance (so a Strict Mode stale
    // instance and the real one are both visible and distinguishable in the log).
    let firstTickLogged = false;

    const tick = async () => {
      if (!firstTickLogged) {
        firstTickLogged = true;
        void mirrorToTerminal("poll: first tick");
      }
      // Claimed synchronously, before any `await`, so a second tick firing while this
      // one is still mid-flight (e.g. a slow cold heartbeat in a debug build widening
      // the window past the 8s poll period) can never slip through the same gap and
      // fire a second concurrent load — the bug that produced 4 overlapping loads.
      if (cancelled || pollBusy || checkingRef.current) return;
      pollBusy = true;

      try {
        const heartbeat = await fm26LiveAdapter.getHeartbeat();
        if (cancelled || heartbeat.state === "unresolved") return;

        if (heartbeat.state === "not_found") {
          // Only a confirmed "fm.exe isn't running" dismounts — never a transient
          // unresolved read, so a save-switch blip can't strand the poll dormant.
          if (heartbeatBaselineRef.current !== null) {
            heartbeatBaselineRef.current = null;
            setSnapshot(initialSnapshot);
          }
          return;
        }

        // heartbeat.state === "connected"
        const baseline = heartbeatBaselineRef.current;
        const clubChanged = baseline !== null && heartbeat.clubUid !== null && heartbeat.clubUid !== baseline.clubUid;
        const dateChanged = baseline !== null && heartbeat.gameDate !== null && heartbeat.gameDate !== baseline.gameDate;
        // No baseline at all covers both "FMT just launched into an already-running
        // save" (auto-load) and "was disconnected, FM/save is back" (auto-reconnect).
        if (baseline !== null && !clubChanged && !dateChanged) return;

        // Auto-load on startup (Settings > User Preferences) only gates the very
        // first load of a session — once hasConnectedOnceRef flips (any load,
        // manual or automatic), disconnect/reconnect and save-switch auto-refresh
        // proceed exactly as T274 shipped, regardless of this preference.
        if (baseline === null && !hasConnectedOnceRef.current && !autoLoadOnStartup) {
          return;
        }

        if (baseline !== null && clubChanged && heartbeat.clubName) {
          setSwitchFlash(heartbeat.clubName);
        }

        await checkConnection();
      } finally {
        setSwitchFlash(null);
        pollBusy = false;
      }
    };

    // `setInterval` only fires after the first full period — without this, auto-load
    // on launch would wait a full POLL_MS for no reason before even checking once.
    void tick();
    const interval = window.setInterval(() => void tick(), POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [checkConnection, autoLoadOnStartup]);

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
          loadStageHistory={loadStageHistory}
          onRefresh={checkConnection}
          switchFlash={switchFlash}
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
