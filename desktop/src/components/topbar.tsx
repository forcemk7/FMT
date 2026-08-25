"use client";

import { ChevronLeft, ChevronRight, Command, RefreshCw, Search } from "lucide-react";
import type { Screen } from "@/components/app-sidebar";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { LiveFootballSnapshot } from "@/domain/adapters";

function syncLabel(value: string | null) {
  if (!value) return "Not synced";
  const elapsed = Math.max(0, Date.now() - Number(value));
  if (elapsed < 60_000) return "Synced just now";
  return `Synced ${Math.max(1, Math.round(elapsed / 60_000))}m ago`;
}

function connectionLabel(snapshot: LiveFootballSnapshot) {
  const status = snapshot.status;
  if (status.state === "connected") return "FM26 live read";
  if (status.processDetected) return "Read not ready";
  return "Waiting for FM26";
}

function connectionDetail(snapshot: LiveFootballSnapshot) {
  const status = snapshot.status;
  if (status.state === "connected") {
    return `${status.managedSquadPlayers} squad`;
  }
  if (status.failureStage) return status.failureStage.replaceAll("_", " ");
  return syncLabel(status.lastSync);
}

export function Topbar({
  search,
  onSearch,
  snapshot,
  screen,
  checking,
  onRefresh,
  canGoBack,
  canGoForward,
  onGoBack,
  onGoForward,
}: {
  search: string;
  onSearch: (value: string) => void;
  snapshot: LiveFootballSnapshot;
  screen: Screen;
  checking: boolean;
  onRefresh: () => Promise<unknown>;
  canGoBack: boolean;
  canGoForward: boolean;
  onGoBack: () => void;
  onGoForward: () => void;
}) {
  const connected = snapshot.status.state === "connected";
  const club = snapshot.clubs.find((item) => item.id === snapshot.managedClubId);

  return (
    <header className="topbar">
      <div className="topbar-left-cluster">
        <div className="topbar-history-controls" aria-label="Navigation history">
          <Button variant="ghost" size="icon" aria-label="Go back" onClick={onGoBack} disabled={!canGoBack}>
            <ChevronLeft aria-hidden="true" />
          </Button>
          <Button variant="ghost" size="icon" aria-label="Go forward" onClick={onGoForward} disabled={!canGoForward}>
            <ChevronRight aria-hidden="true" />
          </Button>
        </div>

        <div className="screen-context">
          <strong>{screen}</strong>
          <span>
            {club?.name ?? "Active club"} <i /> {snapshot.season ?? "Active save"}
          </span>
        </div>
      </div>

      <div className="search-wrap">
        <Search aria-hidden="true" />
        <Input
          aria-label="Search squad players"
          placeholder={connected ? "Search squad…" : "Load the active FM26 save to search"}
          value={search}
          onChange={(event) => onSearch(event.target.value)}
          disabled={!connected}
        />
        <span className="keyboard-hint">
          <Command aria-hidden="true" /> K
        </span>
      </div>

      <div className="topbar-actions">
        <div className="sync-badge">
          <span className={connected ? "live-dot" : "neutral-dot"} />
          <span>{connectionLabel(snapshot)}</span>
          <i />
          <span>{connectionDetail(snapshot)}</span>
        </div>
        <Button variant="outline" size="icon" aria-label="Reload active save" onClick={onRefresh} disabled={checking}>
          <RefreshCw className={checking ? "spin" : undefined} aria-hidden="true" />
        </Button>
      </div>
    </header>
  );
}
