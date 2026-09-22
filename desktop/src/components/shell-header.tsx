"use client";

import { useEffect, useId, useRef, useState, type RefObject } from "react";
import {
  ChevronDown,
  HandCoins,
  LayoutDashboard,
  Menu,
  RefreshCw,
  Search,
  Settings,
  UsersRound,
} from "lucide-react";
import type { Tooltip as TooltipPrimitive } from "@base-ui/react/tooltip";
import { invoke } from "@tauri-apps/api/core";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { LiveFootballSnapshot } from "@/domain/adapters";
import { isDashViewId } from "@/domain/dashboard-views";
import { loadStageLabel, shellLiveSummary } from "@/domain/fmt-terminal-log";

export type Screen =
  | "Dashboard"
  | "Squad"
  | "HoYD"
  | "General Manager"
  | "Loan Manager"
  | "Player Profile"
  | "Club Profile"
  | "Settings"
  | "Movers"
  | "Best players"
  | "Best talent"
  | "Match experience"
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
  { label: "Loan Manager", short: "Loans", live: true, icon: UsersRound },
  { label: "HoYD", short: "HoYD", live: true, icon: UsersRound },
  { label: "General Manager", short: "GM", live: true, icon: UsersRound },
];

/** Collapse the horizontal tab row when the header can't fit it cleanly. */
const NAV_COMPACT_BELOW = 1020;

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
      {navigation.map(({ label, short, icon: Icon }) => (
        <button
          key={label}
          type="button"
          className={cn(
            className,
            activeNav === label && "is-active",
          )}
          onClick={() => {
            onNavigate(label);
            onPicked?.();
          }}
          aria-label={label}
        >
          {Icon ? <Icon aria-hidden="true" /> : null}
          <span>{short}</span>
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
  searchInputRef,
  snapshot,
  checking,
  loadStageHistory,
  onRefresh,
  switchFlash,
}: {
  screen: Screen;
  onNavigate: (screen: Screen) => void;
  search: string;
  onSearch: (value: string) => void;
  searchInputRef?: RefObject<HTMLInputElement | null>;
  snapshot: LiveFootballSnapshot;
  checking: boolean;
  /** Ordered stage keys seen so far this load, for the loading tooltip's compact log (T274). */
  loadStageHistory?: string[];
  onRefresh: () => Promise<unknown>;
  /** Brief "Switched to {club}" text after the auto-poll detects a different save (T274). */
  switchFlash?: string | null;
}) {
  const connected = snapshot.status.state === "connected";
  const activeNav =
    screen === "Player Profile" || screen === "Club Profile"
      ? "Squad"
      : isDashViewId(screen)
        ? "Dashboard"
        : screen;
  const liveSummary = shellLiveSummary(snapshot);

  const headerRef = useRef<HTMLElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [compact, setCompact] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuId = useId();
  // Only one of the two load-control Tooltips is ever mounted at a time (connected
  // pill vs. not-connected button), so one shared actionsRef is enough for both.
  const loadTooltipActionsRef = useRef<TooltipPrimitive.Root.Actions>(null);

  // A tooltip left open from hovering through a load (nice — shows the log/detail
  // live) shouldn't require the user to move the mouse away and back just to dismiss
  // it once the load is done; close it the moment `checking` finishes.
  useEffect(() => {
    if (!checking) loadTooltipActionsRef.current?.close();
  }, [checking]);

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
            ref={searchInputRef}
            type="search"
            name="fmt-squad-search"
            aria-label="Search players"
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

        {connected ? (
          <Tooltip actionsRef={loadTooltipActionsRef}>
            <TooltipTrigger
              render={<div />}
              className={cn("shell-live-pill", checking && "is-loading")}
              aria-label={`Live: ${liveSummary.clubName}`}
            >
              <span className="live-dot" aria-hidden="true" />
              <strong>{checking && switchFlash ? "Switching…" : liveSummary.clubName}</strong>
              <button
                type="button"
                className="shell-live-refresh"
                onClick={(event) => {
                  event.stopPropagation();
                  void onRefresh();
                }}
                disabled={checking}
                title="Force refresh"
                aria-label="Force refresh live data"
              >
                <RefreshCw aria-hidden="true" className={cn("shell-load-icon", checking && "spin")} />
              </button>
            </TooltipTrigger>
            <TooltipContent>
              {checking && switchFlash ? (
                <div>
                  <dl className="shell-status-grid">
                    <dt>Switching to</dt>
                    <dd>{switchFlash}</dd>
                  </dl>
                  {loadStageHistory && loadStageHistory.length > 0 ? (
                    <ol className="shell-load-log">
                      {loadStageHistory.map((stage, index) => (
                        <li key={`${stage}-${index}`} aria-current={index === loadStageHistory.length - 1}>
                          {loadStageLabel(stage)}
                        </li>
                      ))}
                    </ol>
                  ) : null}
                </div>
              ) : (
                <dl className="shell-status-grid">
                  <dt>Club</dt>
                  <dd>{liveSummary.clubName}</dd>
                  <dt>Players</dt>
                  <dd>{liveSummary.playerCount}</dd>
                  <dt>As of</dt>
                  <dd>{liveSummary.gameDate ?? "unavailable"}</dd>
                </dl>
              )}
            </TooltipContent>
          </Tooltip>
        ) : (
          <Tooltip actionsRef={loadTooltipActionsRef}>
            <TooltipTrigger
              type="button"
              className={cn("shell-load", checking ? "is-loading" : "is-needs-load")}
              onClick={() => void onRefresh()}
              disabled={checking}
              aria-label={checking ? "Loading" : "Load Data"}
            >
              <span className="offline-dot" aria-hidden="true" />
              <strong>{checking ? "Loading…" : "Load"}</strong>
              <RefreshCw aria-hidden="true" className={cn("shell-load-icon", checking && "spin")} />
            </TooltipTrigger>
            {checking && loadStageHistory && loadStageHistory.length > 0 ? (
              <TooltipContent>
                <ol className="shell-load-log">
                  {loadStageHistory.map((stage, index) => (
                    <li key={`${stage}-${index}`} aria-current={index === loadStageHistory.length - 1}>
                      {loadStageLabel(stage)}
                    </li>
                  ))}
                </ol>
              </TooltipContent>
            ) : null}
          </Tooltip>
        )}

        <button
          type="button"
          onClick={() => {
            if (!("__TAURI_INTERNALS__" in window)) return;
            void invoke("open_external", { url: "https://buymeacoffee.com/mrramirez" }).catch(() => {});
          }}
          className={cn(buttonVariants({ variant: "ghost", size: "icon" }), "shell-bmc")}
          title="Support FMT's development"
          aria-label="Support FMT's development"
        >
          <HandCoins aria-hidden="true" />
        </button>

        <Button
          variant="ghost"
          size="icon"
          title="Settings & diagnostics"
          aria-label="Settings & diagnostics"
          className={cn(screen === "Settings" && "is-active")}
          onClick={() => onNavigate("Settings")}
        >
          <Settings />
        </Button>
      </div>
    </header>
  );
}
