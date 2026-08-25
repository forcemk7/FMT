"use client";

import {
  ChevronLeft,
  Map,
  Settings,
  UsersRound,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type Screen =
  | "Squad"
  | "Roadmap"
  | "Player Profile"
  | "Club Profile"
  | "Settings";

const navigation = [
  { label: "Squad", icon: UsersRound, hint: "Live" },
  { label: "Roadmap", icon: Map, hint: "Later" },
] satisfies { label: Screen; icon: typeof UsersRound; hint: string }[];

export function AppSidebar({
  screen,
  onNavigate,
}: {
  screen: Screen;
  onNavigate: (screen: Screen) => void;
}) {
  return (
    <aside className="app-sidebar">
      <button className="brand" onClick={() => onNavigate("Squad")} aria-label="Go to squad">
        <span className="brand-mark" aria-hidden="true"><span /></span>
        <span className="brand-copy"><strong>FMT</strong><small>club desk</small></span>
      </button>

      <nav className="nav-list" aria-label="Main navigation">
        {navigation.map(({ label, icon: Icon, hint }) => (
          <Button
            key={label}
            variant="ghost"
            className={cn("nav-item", screen === label && "nav-item-active")}
            onClick={() => onNavigate(label)}
          >
            <Icon data-icon="inline-start" />
            <span>{label}</span>
            <small className="nav-hint">{hint}</small>
          </Button>
        ))}
      </nav>

      <div className="sidebar-spacer" />
      <Button
        variant="ghost"
        className={cn("nav-item", screen === "Settings" && "nav-item-active")}
        onClick={() => onNavigate("Settings")}
      >
        <Settings data-icon="inline-start" />
        <span>Settings</span>
      </Button>
      <div className="sidebar-footer">
        <span><strong>Step 1</strong><small>Squad · attrs · history</small></span>
      </div>
      <button className="sidebar-collapse" aria-label="Collapse sidebar" type="button">
        <ChevronLeft />
      </button>
    </aside>
  );
}
