"use client";

import {
  Activity,
  Building2,
  CalendarDays,
  ChevronDown,
  Gamepad2,
  Images,
  Network,
  SlidersHorizontal,
  UserCog,
  UserRound,
  Users,
} from "lucide-react";
import type { LiveFootballSnapshot } from "@/domain/adapters";
import {
  isAffiliateClubTeam,
  sortClubTeamsForSquadDesk,
  squadTeamDisplayName,
  teamTypeDisplayLabel,
} from "@/domain/live-data";
import { setPreference, usePreferences } from "@/domain/preferences";
import { isTelemetryConfigured, useLastSent } from "@/domain/telemetry";
import { useGraphicsPacksStatus } from "@/components/graphics-packs-panel";
import { getVersion } from "@tauri-apps/api/app";
import { useEffect, useMemo, useState, type ReactNode } from "react";

function readable(value: string | null | undefined) {
  if (!value) return "None";
  return value.replaceAll("_", " ").replaceAll("-", " ");
}

function memorySafetyLabel(access: string) {
  if (access === "not_checked") return "Not checked";
  if (access.includes("read")) return "Read-only";
  return readable(access);
}

type DiagnosticTone = "green" | "yellow" | "red";

type DiagCell = {
  title: string;
  status: string;
  tone: DiagnosticTone;
  critical?: boolean;
  wide?: boolean;
};

function DiagnosticCellView({ title, status, tone, wide }: DiagCell) {
  return (
    <div
      className={["diagnostic-cell", `tone-${tone}`, wide ? "diagnostic-hash" : ""]
        .filter(Boolean)
        .join(" ")}
    >
      <dt>
        <span className="diagnostic-tone" aria-hidden="true" />
        {title}
      </dt>
      <dd>{status.trim() || "none"}</dd>
    </div>
  );
}

function toneIf(
  ok: boolean,
  whenOk: DiagnosticTone = "green",
  whenBad: DiagnosticTone = "red",
): DiagnosticTone {
  return ok ? whenOk : whenBad;
}

function tonePresent(
  value: string | number | null | undefined,
  opts?: { empty?: DiagnosticTone; zeroOk?: boolean },
): DiagnosticTone {
  const emptyTone = opts?.empty ?? "yellow";
  if (value === null || value === undefined) return emptyTone;
  if (typeof value === "number") {
    if (value === 0 && !opts?.zeroOk) return emptyTone;
    return "green";
  }
  const text = value.trim();
  if (
    !text ||
    text === "None" ||
    text === "none" ||
    text === "Unavailable" ||
    text === "Not checked" ||
    text === "Not run" ||
    text === "not run" ||
    text === "Not verified" ||
    text === "Not detected" ||
    text === "Not readable"
  ) {
    return emptyTone;
  }
  return "green";
}

/** Optimistic floor: all green → green; any critical red → red; else yellow. */
function sectionTone(cells: DiagCell[]): DiagnosticTone {
  if (!cells.length) return "yellow";
  if (cells.every((cell) => cell.tone === "green")) return "green";
  if (cells.some((cell) => cell.critical && cell.tone === "red")) return "red";
  return "yellow";
}

function cellByTitle(cells: DiagCell[], title: string): DiagCell | undefined {
  return cells.find((cell) => cell.title === title);
}

/**
 * Two-column grid without holes: wide cells go last (a wide cell mid-list
 * strands the half cell before it), and an odd half-cell count stretches its
 * last cell across the row.
 */
function packCells(cells: DiagCell[]): DiagCell[] {
  const half = cells.filter((cell) => !cell.wide);
  const wide = cells.filter((cell) => cell.wide);
  if (half.length % 2 === 1) {
    half[half.length - 1] = { ...half[half.length - 1], wide: true };
  }
  return [...half, ...wide];
}

function SettingsGroup({
  id,
  icon,
  title,
  meta,
  tone,
  cells,
  children,
}: {
  id: string;
  icon: ReactNode;
  title: string;
  meta?: string;
  tone?: DiagnosticTone;
  cells?: DiagCell[];
  children?: ReactNode;
}) {
  return (
    <details className="settings-expand" id={id}>
      <summary>
        {icon}
        <strong className="settings-section-label">{title}</strong>
        <span className="settings-expand-meta">
          {tone ? (
            <span className={`settings-section-tone tone-${tone}`} aria-label={`${tone} status`} />
          ) : null}
          {meta ? <b>{meta}</b> : null}
          <ChevronDown className="settings-expand-chevron" aria-hidden="true" />
        </span>
      </summary>
      <div className="settings-expand-body">
        {children ?? (
          <dl className="settings-diagnostics-grid">
            {packCells(cells ?? []).map((cell, index) => (
              <DiagnosticCellView key={`${cell.title}:${index}`} {...cell} />
            ))}
          </dl>
        )}
      </div>
    </details>
  );
}

/** A settings-diagnostics-grid cell with a real control instead of a read-only status. */
function PreferenceToggleCell({
  title,
  description,
  checked,
  onChange,
}: {
  title: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="diagnostic-cell settings-pref-cell">
      <dt>{title}</dt>
      <dd>
        <button
          type="button"
          role="switch"
          aria-checked={checked}
          aria-label={title}
          className={`settings-pref-toggle${checked ? " is-on" : ""}`}
          onClick={() => onChange(!checked)}
        >
          <i aria-hidden="true" />
        </button>
        {description ? <span className="settings-pref-desc">{description}</span> : null}
      </dd>
    </div>
  );
}

export function SettingsScreen({
  snapshot,
}: {
  snapshot: LiveFootballSnapshot;
}) {
  const status = snapshot.status;
  const preferences = usePreferences();
  const lastSent = useLastSent();
  const [appVersion, setAppVersion] = useState<string | null>(null);
  const graphics = useGraphicsPacksStatus();
  const clubTeams = useMemo(
    () =>
      sortClubTeamsForSquadDesk(
        (snapshot.clubTeams ?? []).filter(
          (team) => team.rosterLen > 0 || team.isManagerTeam,
        ),
      ),
    [snapshot.clubTeams],
  );
  const managedClubName = useMemo(() => {
    const clubId = snapshot.managedClubId;
    if (!clubId) return null;
    return snapshot.clubs.find((club) => club.id === clubId)?.name ?? null;
  }, [snapshot.clubs, snapshot.managedClubId]);

  const backendCells: DiagCell[] = useMemo(
    () =>
      (status.diagnosticCells ?? []).map((cell) => ({
        title: cell.title,
        status: cell.status,
        tone: cell.tone ?? "yellow",
        wide: cell.status.length > 80,
      })),
    [status.diagnosticCells],
  );

  const affiliateClubsCount = useMemo(
    () =>
      new Set(
        (snapshot.clubTeams ?? [])
          .filter(isAffiliateClubTeam)
          .map((team) => team.clubId || team.clubName || team.teamUid),
      ).size,
    [snapshot.clubTeams],
  );

  // Club name + team type, so two teams of one club (e.g. First Team and
  // Reserves) don't read as a duplicate — same pairing as the Profile ME tab.
  const matchExperienceTeams = useMemo(
    () =>
      (snapshot.clubTeams ?? [])
        .filter(
          (team) =>
            team.matchExperienceOnly ||
            team.affiliationType === 0x01 ||
            team.affiliationType === 0x03,
        )
        .map((team) => {
          const club = team.clubName?.trim() || team.name.trim();
          const type = team.teamType === 0 ? null : teamTypeDisplayLabel(team.teamType);
          return type ? `${club} ${type}` : club;
        }),
    [snapshot.clubTeams],
  );

  useEffect(() => {
    if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) return;
    getVersion().then(setAppVersion).catch(() => setAppVersion(null));
  }, []);

  const backendCell = (title: string, critical = false): DiagCell => {
    const fromBackend = cellByTitle(backendCells, title);
    return {
      title,
      status: fromBackend?.status ?? "Unavailable",
      tone: fromBackend?.tone ?? "yellow",
      critical,
      wide: (fromBackend?.status.length ?? 0) > 60,
    };
  };

  const fm26Cells: DiagCell[] = [
    {
      title: "Connection state",
      status: readable(status.state),
      tone: toneIf(status.state === "connected"),
      critical: true,
    },
    {
      title: "Process ID",
      status: status.processDetected ? String(status.processId) : "Not detected",
      tone: toneIf(Boolean(status.processDetected)),
      critical: true,
    },
    {
      title: "Executable",
      status: status.processPath ?? "Unavailable",
      tone: tonePresent(status.processPath),
      critical: true,
      wide: true,
    },
    {
      title: "Memory access",
      status: memorySafetyLabel(status.memoryAccess),
      tone: status.memoryAccess.includes("read")
        ? "green"
        : status.memoryAccess === "denied"
          ? "red"
          : "yellow",
      critical: true,
    },
    {
      title: "Windows error",
      status: status.windowsErrorCode != null ? String(status.windowsErrorCode) : "None",
      tone: status.windowsErrorCode != null ? "red" : "green",
      critical: true,
    },
    {
      title: "FM26 build",
      status: status.gameBuild ?? "Unavailable",
      tone: tonePresent(status.gameBuild),
      critical: true,
    },
    {
      title: "Architecture",
      status: status.architecture ?? "Unavailable",
      tone: tonePresent(status.architecture),
    },
    {
      // Only hashed when the version alone doesn't pick an entity map.
      title: "Executable SHA-256",
      status:
        status.executableSha256 ??
        (status.entityMapStatus === "matched" ? "Not needed" : "Unavailable"),
      tone:
        status.executableSha256 || status.entityMapStatus === "matched" ? "green" : "yellow",
      wide: true,
    },
    {
      title: "Module base",
      status: status.moduleBase ?? "Unavailable",
      tone: tonePresent(status.moduleBase),
    },
    {
      title: "Entity map",
      status:
        status.entityMapStatus === "matched"
          ? status.entityMapProfileId ?? "Matched"
          : status.entityMapStatus === "missing"
            ? "No match for this build"
            : "Not checked",
      tone:
        status.entityMapStatus === "matched"
          ? "green"
          : status.entityMapStatus === "missing"
            ? "red"
            : "yellow",
      critical: true,
    },
    {
      title: "Last sync",
      status: status.lastSync ? new Date(Number(status.lastSync)).toLocaleString() : "None",
      tone: tonePresent(status.lastSync),
    },
    {
      title: "Failure stage",
      status: readable(status.failureStage),
      tone: status.failureStage ? "red" : "green",
      critical: true,
    },
    {
      title: "Data error",
      status: snapshot.dataError?.trim() || "None",
      tone: snapshot.dataError?.trim() ? "red" : "green",
      critical: true,
    },
  ];

  const saveCells: DiagCell[] = [
    {
      title: "In-game date",
      status: snapshot.gameDate?.trim() || "Unavailable",
      tone: tonePresent(snapshot.gameDate),
      critical: true,
    },
  ];

  const managerCells: DiagCell[] = [
    {
      title: "Manager name",
      status: snapshot.managerName ?? "Unavailable",
      tone: tonePresent(snapshot.managerName),
      critical: true,
    },
    {
      title: "Manager registry pointer",
      status: status.entityRoot ?? "Unavailable",
      tone: tonePresent(status.entityRoot),
      critical: true,
    },
    {
      title: "Active manager pointer",
      status: status.savePointer ?? "Unavailable",
      tone: tonePresent(status.savePointer),
      critical: true,
    },
    backendCell("Human managers"),
  ];

  const clubCells: DiagCell[] = [
    {
      title: "Managed club pointer",
      status: status.managedClubPointer ?? "Unavailable",
      tone: tonePresent(status.managedClubPointer),
      critical: true,
    },
    {
      title: "Managed club id",
      status: snapshot.managedClubId ?? "Unavailable",
      tone: tonePresent(snapshot.managedClubId),
      critical: true,
    },
    {
      title: "Managed club name",
      status: managedClubName ?? "Unavailable",
      tone: tonePresent(managedClubName),
      critical: true,
    },
  ];

  const affiliationsCells: DiagCell[] = [
    backendCell("Affiliation links"),
    backendCell("Players Go On Loan filter"),
    backendCell("Affiliate clubs loaded"),
    backendCell("Excluded affiliation links"),
    backendCell("Dropped loan-off feeders"),
    backendCell("Duplicate affiliation links"),
    backendCell("Unresolved affiliate partners", true),
    {
      title: "Match experience affiliate teams",
      status: matchExperienceTeams.join(", ") || "none",
      tone: "green",
      wide: matchExperienceTeams.join(", ").length > 60,
    },
  ];

  const teamsCells: DiagCell[] = clubTeams.length
    ? clubTeams.map((team) => ({
        title: squadTeamDisplayName(team, managedClubName),
        status: `${team.rosterLen} players`,
        tone: team.rosterLen > 0 ? ("green" as const) : ("red" as const),
        critical: Boolean(team.isManagerTeam) && team.rosterLen === 0,
      }))
    : [{ title: "Teams", status: "none", tone: "yellow" as const, critical: true }];

  const playersCells: DiagCell[] = [
    {
      title: "Players loaded",
      status: String(status.playersLoaded),
      tone: tonePresent(status.playersLoaded, { zeroOk: false }),
      critical: true,
    },
    {
      title: "Club employees",
      status: String(status.clubEmployees || status.managedSquadPlayers),
      tone: tonePresent(status.clubEmployees || status.managedSquadPlayers, {
        zeroOk: false,
      }),
    },
    {
      title: "Squad collection pointer",
      status: status.playerCollectionPointer ?? "Unavailable",
      tone: tonePresent(status.playerCollectionPointer),
      critical: true,
    },
    backendCell("Skipped squad slots"),
    backendCell("Name fallback"),
  ];

  const graphicsCells: DiagCell[] = [
    {
      title: "Graphics folder",
      status: graphics?.graphicsPath?.trim() || "Unavailable",
      tone: !graphics || graphics.loading ? "yellow" : toneIf(Boolean(graphics.graphicsExists)),
      wide: true,
    },
    ...(!graphics || graphics.loading
      ? []
      : graphics.packs.length
        ? graphics.packs.map((pack) => ({
            title: pack.kind,
            status: pack.name,
            tone: "green" as const,
          }))
        : [{ title: "Packs", status: "none", tone: "green" as const }]),
  ];

  const diagnosticsCells: DiagCell[] = [
    {
      title: "FMT version",
      status: appVersion ?? "Unavailable",
      tone: tonePresent(appVersion),
    },
    {
      title: "Last sent",
      status: lastSent ? lastSent.at.toLocaleString() : "None",
      tone: lastSent ? toneIf(lastSent.ok) : "yellow",
    },
    {
      title: "Anonymous id",
      status: preferences.telemetryId || "Not generated yet",
      tone: tonePresent(preferences.telemetryId),
      wide: true,
    },
    {
      title: "Last data sent",
      status: lastSent?.data ?? "None",
      tone: lastSent ? toneIf(lastSent.ok) : "yellow",
      wide: true,
    },
  ];

  return (
    <main className="screen settings-screen" aria-label="Settings">
      <section className="settings-list settings-list-preferences">
        <SettingsGroup
          id="settings-preferences"
          icon={<SlidersHorizontal aria-hidden="true" />}
          title="User Preferences"
        >
          <dl className="settings-diagnostics-grid">
            <PreferenceToggleCell
              title="Auto-load on startup"
              description="Automatically loads the live save when FMT opens. Turn off to require clicking Load."
              checked={preferences.autoLoadOnStartup}
              onChange={(checked) => setPreference("autoLoadOnStartup", checked)}
            />
            <PreferenceToggleCell
              title="Hide potential ability (PA)"
              description="Masks PA as “?” everywhere it's shown, including the Dashboard biggest-talent card."
              checked={preferences.hidePA}
              onChange={(checked) => setPreference("hidePA", checked)}
            />
            <PreferenceToggleCell
              title="Larger interface"
              description="Scales text and controls up for readability. Off keeps FMT's compact default size."
              checked={preferences.largeUi}
              onChange={(checked) => setPreference("largeUi", checked)}
            />
          </dl>
        </SettingsGroup>

        <SettingsGroup
          id="settings-diagnostics"
          icon={<Activity aria-hidden="true" />}
          title="Diagnostics"
          meta={isTelemetryConfigured() ? "Always on" : "Not configured"}
          tone={sectionTone(diagnosticsCells)}
          cells={diagnosticsCells}
        />
      </section>

      <section className="settings-list">
        <SettingsGroup
          id="settings-graphics"
          icon={<Images aria-hidden="true" />}
          title="Graphics"
          meta={
            !graphics || graphics.loading
              ? "…"
              : graphics.packs.length
                ? `${graphics.packs.length} packs`
                : "None"
          }
          tone={sectionTone(graphicsCells)}
          cells={graphicsCells}
        />

        <SettingsGroup
          id="settings-fm26"
          icon={<Gamepad2 aria-hidden="true" />}
          title="FM26"
          meta={memorySafetyLabel(status.memoryAccess)}
          tone={sectionTone(fm26Cells)}
          cells={fm26Cells}
        />

        <SettingsGroup
          id="settings-save"
          icon={<CalendarDays aria-hidden="true" />}
          title="Save"
          meta={snapshot.gameDate?.trim() || "—"}
          tone={sectionTone(saveCells)}
          cells={saveCells}
        />

        <SettingsGroup
          id="settings-manager"
          icon={<UserCog aria-hidden="true" />}
          title="Manager"
          meta={snapshot.managerName ?? "—"}
          tone={sectionTone(managerCells)}
          cells={managerCells}
        />

        <SettingsGroup
          id="settings-club"
          icon={<Building2 aria-hidden="true" />}
          title="Club"
          meta={managedClubName ?? snapshot.managedClubId ?? "—"}
          tone={sectionTone(clubCells)}
          cells={clubCells}
        />

        <SettingsGroup
          id="settings-affiliations"
          icon={<Network aria-hidden="true" />}
          title="Affiliations"
          meta={affiliateClubsCount ? `${affiliateClubsCount} affiliates` : "—"}
          tone={sectionTone(affiliationsCells)}
          cells={affiliationsCells}
        />

        <SettingsGroup
          id="settings-teams"
          icon={<Users aria-hidden="true" />}
          title="Teams"
          meta={clubTeams.length ? `${clubTeams.length} teams` : "—"}
          tone={sectionTone(teamsCells)}
          cells={teamsCells}
        />

        <SettingsGroup
          id="settings-players"
          icon={<UserRound aria-hidden="true" />}
          title="Players"
          meta={status.playersLoaded ? `${status.playersLoaded} loaded` : "—"}
          tone={sectionTone(playersCells)}
          cells={playersCells}
        />
      </section>
    </main>
  );
}
