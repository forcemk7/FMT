"use client";

import {
  ChevronLeft,
  ChevronRight,
  CircleDashed,
  LayoutDashboard,
  RefreshCw,
  Search,
  Settings,
  UsersRound,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { LiveFootballSnapshot } from "@/domain/adapters";

export type Screen =
  | "Dashboard"
  | "Squad"
  | "Tactic"
  | "HoYD"
  | "General Manager"
  | "Loan Manager"
  | "Technical Director"
  | "Player Profile"
  | "Club Profile"
  | "Settings";

type NavItem = {
  label: Screen;
  short: string;
  live: boolean;
  icon?: typeof LayoutDashboard;
};

const navigation: NavItem[] = [
  { label: "Dashboard", short: "Dashboard", live: true, icon: LayoutDashboard },
  { label: "Squad", short: "Squad", live: true, icon: UsersRound },
  { label: "Tactic", short: "Tactic", live: false },
  { label: "HoYD", short: "HoYD", live: false },
  { label: "General Manager", short: "GM", live: false },
  { label: "Loan Manager", short: "Loans", live: false },
  { label: "Technical Director", short: "TD", live: false },
];

function connectionDetail(snapshot: LiveFootballSnapshot) {
  const status = snapshot.status;
  if (status.state === "connected") return `${status.managedSquadPlayers} squad`;
  if (status.failureStage) return status.failureStage.replaceAll("_", " ");
  return "Not synced";
}

/** Single-row shell: brand · nav · search · Load Data / sync (T141/T144). */
export function ShellHeader({
  screen,
  onNavigate,
  search,
  onSearch,
  snapshot,
  checking,
  onRefresh,
  canGoBack,
  canGoForward,
  onGoBack,
  onGoForward,
}: {
  screen: Screen;
  onNavigate: (screen: Screen) => void;
  search: string;
  onSearch: (value: string) => void;
  snapshot: LiveFootballSnapshot;
  checking: boolean;
  onRefresh: () => Promise<unknown>;
  canGoBack: boolean;
  canGoForward: boolean;
  onGoBack: () => void;
  onGoForward: () => void;
}) {
  const connected = snapshot.status.state === "connected";
  const club = snapshot.clubs.find((item) => item.id === snapshot.managedClubId);
  const activeNav =
    screen === "Player Profile" || screen === "Club Profile" ? "Squad" : screen;
  const needsLoad = !connected;
  const loadLabel = checking ? "Loading…" : needsLoad ? "Load Data" : club?.name ?? "Synced";
  const loadDetail = connected ? connectionDetail(snapshot) : null;

  return (
    <header className="shell-header">
      <button type="button" className="brand" onClick={() => onNavigate("Dashboard")} aria-label="FMT home">
        <span className="brand-mark" aria-hidden="true">
          <span />
        </span>
        <span className="brand-copy">
          <strong>FMT</strong>
          <small>club desk</small>
        </span>
      </button>

      <nav className="shell-nav" aria-label="Main">
        {navigation.map(({ label, short, live, icon: Icon }) => (
          <button
            key={label}
            type="button"
            className={cn(
              "shell-nav-item",
              activeNav === label && "is-active",
              !live && "is-later",
            )}
            onClick={() => onNavigate(label)}
            title={live ? label : `${label} — later (roadmap)`}
            aria-label={live ? label : `${label}, later roadmap`}
          >
            {Icon ? <Icon aria-hidden="true" /> : null}
            <span>{short}</span>
            {!live ? <CircleDashed className="shell-nav-tbd" aria-hidden="true" /> : null}
          </button>
        ))}
      </nav>

      <div className="shell-tools">
        <div className="shell-history" aria-label="History">
          <Button variant="ghost" size="icon" aria-label="Back" onClick={onGoBack} disabled={!canGoBack}>
            <ChevronLeft />
          </Button>
          <Button variant="ghost" size="icon" aria-label="Forward" onClick={onGoForward} disabled={!canGoForward}>
            <ChevronRight />
          </Button>
        </div>

        <div className="search-wrap shell-search">
          <Search aria-hidden="true" />
          <Input
            aria-label="Search squad"
            placeholder={connected ? "Search squad…" : "Load save to search"}
            value={search}
            onChange={(event) => onSearch(event.target.value)}
            disabled={!connected}
          />
        </div>

        <button
          type="button"
          className={cn("shell-load", needsLoad && "is-needs-load", checking && "is-loading")}
          onClick={() => void onRefresh()}
          disabled={checking}
          title={needsLoad ? "Load active FM26 save" : "Reload live squad data"}
          aria-label={needsLoad ? "Load Data" : "Reload live data"}
        >
          <span className={connected ? "live-dot" : "neutral-dot"} aria-hidden="true" />
          <strong>{loadLabel}</strong>
          {loadDetail ? <span>{loadDetail}</span> : null}
          <RefreshCw aria-hidden="true" className={cn("shell-load-icon", checking && "spin")} />
        </button>

        <Button
          variant="ghost"
          size="icon"
          aria-label="Settings"
          className={cn(screen === "Settings" && "is-active")}
          onClick={() => onNavigate("Settings")}
        >
          <Settings />
        </Button>
      </div>
    </header>
  );
}
