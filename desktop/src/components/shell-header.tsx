"use client";

import { useEffect, useId, useRef, useState } from "react";
import {
  ChevronDown,
  CircleDashed,
  LayoutDashboard,
  Menu,
  RefreshCw,
  Search,
  Settings,
  UsersRound,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { LiveFootballSnapshot } from "@/domain/adapters";
import { isDashViewId } from "@/domain/dashboard-views";

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
  | "Settings"
  | "Movers"
  | "Prospects"
  | "HAS Top"
  | "HAS Bottom";

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
  { label: "General Manager", short: "GM", live: true, icon: UsersRound },
  { label: "Loan Manager", short: "Loans", live: true, icon: UsersRound },
  { label: "Technical Director", short: "TD", live: false },
];

/** Collapse the horizontal tab row when the header can't fit it cleanly. */
const NAV_COMPACT_BELOW = 1020;

function connectionDetail(snapshot: LiveFootballSnapshot) {
  const status = snapshot.status;
  if (status.state === "connected") return `${status.managedSquadPlayers} squad`;
  if (status.failureStage) return status.failureStage.replaceAll("_", " ");
  return "Not synced";
}

function NavButtons({
  activeNav,
  onNavigate,
  className,
  onPicked,
}: {
  activeNav: string;
  onNavigate: (screen: Screen) => void;
  className?: string;
  onPicked?: () => void;
}) {
  return (
    <>
      {navigation.map(({ label, short, live, icon: Icon }) => (
        <button
          key={label}
          type="button"
          className={cn(
            className,
            activeNav === label && "is-active",
            !live && "is-later",
          )}
          onClick={() => {
            onNavigate(label);
            onPicked?.();
          }}
          title={live ? label : `${label} — later (roadmap)`}
          aria-label={live ? label : `${label}, later roadmap`}
        >
          {Icon ? <Icon aria-hidden="true" /> : null}
          <span>{short}</span>
          {!live ? <CircleDashed className="shell-nav-tbd" aria-hidden="true" /> : null}
        </button>
      ))}
    </>
  );
}

/** Single-row shell: nav · search · Load Data / sync. History lives on desks that need it. */
export function ShellHeader({
  screen,
  onNavigate,
  search,
  onSearch,
  snapshot,
  checking,
  onRefresh,
}: {
  screen: Screen;
  onNavigate: (screen: Screen) => void;
  search: string;
  onSearch: (value: string) => void;
  snapshot: LiveFootballSnapshot;
  checking: boolean;
  onRefresh: () => Promise<unknown>;
}) {
  const connected = snapshot.status.state === "connected";
  const club = snapshot.clubs.find((item) => item.id === snapshot.managedClubId);
  const activeNav =
    screen === "Player Profile" || screen === "Club Profile"
      ? "Squad"
      : isDashViewId(screen)
        ? "Dashboard"
        : screen;
  const needsLoad = !connected;
  const loadLabel = checking ? "Loading…" : needsLoad ? "Load Data" : club?.name ?? "Synced";
  const loadDetail = connected ? connectionDetail(snapshot) : null;

  const headerRef = useRef<HTMLElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [compact, setCompact] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuId = useId();

  const activeItem =
    navigation.find((item) => item.label === activeNav) ?? navigation[0];

  useEffect(() => {
    const node = headerRef.current;
    if (!node || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width ?? node.clientWidth;
      setCompact(width < NAV_COMPACT_BELOW);
    });
    observer.observe(node);
    setCompact(node.clientWidth < NAV_COMPACT_BELOW);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!compact) setMenuOpen(false);
  }, [compact]);

  useEffect(() => {
    if (!menuOpen) return;
    const onPointer = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  return (
    <header className="shell-header" ref={headerRef}>
      {compact ? (
        <div className="shell-nav-compact" ref={menuRef}>
          <button
            type="button"
            className="shell-nav-trigger"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            aria-controls={menuId}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <Menu aria-hidden="true" />
            <span>{activeItem.short}</span>
            <ChevronDown aria-hidden="true" className={cn(menuOpen && "is-open")} />
          </button>
          {menuOpen ? (
            <div id={menuId} className="shell-nav-menu" role="menu" aria-label="Main">
              <NavButtons
                activeNav={activeNav}
                onNavigate={onNavigate}
                className="shell-nav-menu-item"
                onPicked={() => setMenuOpen(false)}
              />
            </div>
          ) : null}
        </div>
      ) : (
        <nav className="shell-nav" aria-label="Main">
          <NavButtons
            activeNav={activeNav}
            onNavigate={onNavigate}
            className="shell-nav-item"
          />
        </nav>
      )}

      <div className="shell-tools">
        <div className="search-wrap shell-search">
          <Search aria-hidden="true" />
          <Input
            type="search"
            name="fmt-squad-search"
            aria-label="Search squad"
            placeholder={connected ? "Search squad…" : "Load save to search"}
            value={search}
            onChange={(event) => onSearch(event.target.value)}
            disabled={!connected}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            spellCheck={false}
            data-1p-ignore
            data-lpignore="true"
            data-form-type="other"
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
