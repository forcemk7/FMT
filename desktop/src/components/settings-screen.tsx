"use client";

import {
  Building2,
  ChevronDown,
  Gamepad2,
  Images,
  Network,
  RefreshCw,
  Sigma,
  UserRound,
  Users,
} from "lucide-react";
import type { LiveFootballSnapshot } from "@/domain/adapters";
import { FRONTEND_CALCULATION_CARDS } from "@/domain/has-score";
import { sortClubTeamsForSquadDesk, squadTeamDisplayName } from "@/domain/live-data";
import { Button } from "@/components/ui/button";
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

function mappingCoverageLabel(
  coverage: NonNullable<LiveFootballSnapshot["status"]["mappingCoverage"]> | undefined,
) {
  if (!coverage?.length) return "None";
  return coverage
    .map(
      (row) =>
        `${row.section}: ${row.validated} validated · ${row.candidate} candidate · ${row.unmapped} unmapped`,
    )
    .join("; ");
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

function SettingsGroup({
  id,
  icon,
  title,
  subtitle,
  meta,
  tone,
  action,
  cells,
}: {
  id: string;
  icon: ReactNode;
  title: string;
  subtitle: string;
  meta: string;
  tone: DiagnosticTone;
  action?: ReactNode;
  cells: DiagCell[];
}) {
  return (
    <details className="settings-expand" id={id}>
      <summary>
        {icon}
        <div>
          <strong>{title}</strong>
          <span>{subtitle}</span>
        </div>
        <span className="settings-expand-meta">
          <span className={`settings-section-tone tone-${tone}`} aria-label={`${tone} status`} />
          <b>{meta}</b>
          <ChevronDown className="settings-expand-chevron" aria-hidden="true" />
        </span>
      </summary>
      <div className="settings-expand-body">
        {action ? <div className="settings-expand-actions">{action}</div> : null}
        <dl className="settings-diagnostics-grid">
          {cells.map((cell, index) => (
            <DiagnosticCellView key={`${cell.title}:${index}`} {...cell} />
          ))}
        </dl>
      </div>
    </details>
  );
}

export function SettingsScreen({
  snapshot,
  checking,
  onRefresh,
}: {
  snapshot: LiveFootballSnapshot;
  checking: boolean;
  onRefresh: () => Promise<unknown>;
}) {
  const status = snapshot.status;
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

  useEffect(() => {
    if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) return;
    getVersion().then(setAppVersion).catch(() => setAppVersion(null));
  }, []);

  const fm26Cells: DiagCell[] = [
    {
      title: "Connection state",
      status: readable(status.state),
      tone: toneIf(status.state === "connected"),
      critical: true,
    },
    {
      title: "Process",
      status: status.processDetected ? `Detected · PID ${status.processId}` : "Not detected",
      tone: toneIf(Boolean(status.processDetected)),
      critical: true,
    },
    {
      title: "Executable",
      status: status.processPath ?? "Unavailable",
      tone: tonePresent(status.processPath),
      critical: true,
    },
    {
      title: "Memory access",
      status: readable(status.memoryAccess),
      tone: toneIf(status.memoryAccess.includes("read"), "green", "red"),
      critical: true,
    },
    {
      title: "Can write memory",
      status: status.canWriteMemory ? "Yes" : "No",
      tone: "green",
    },
    {
      title: "Memory safety",
      status: memorySafetyLabel(status.memoryAccess),
      tone: toneIf(status.memoryAccess.includes("read"), "green", "yellow"),
    },
    {
      title: "Read-only access flags",
      status: status.handleAccessFlags ?? "Unavailable",
      tone: tonePresent(status.handleAccessFlags),
      wide: true,
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
      title: "Product version",
      status: status.productVersion ?? "Unavailable",
      tone: tonePresent(status.productVersion),
    },
    {
      title: "Architecture",
      status: status.architecture ?? "Unavailable",
      tone: tonePresent(status.architecture),
    },
    {
      title: "Executable SHA-256",
      status: status.executableSha256 ?? "Unavailable",
      tone: tonePresent(status.executableSha256),
      wide: true,
    },
    {
      title: "Module base",
      status: status.moduleBase ?? "Unavailable",
      tone: tonePresent(status.moduleBase),
    },
    {
      title: "Memory probe",
      status: status.executableHeaderValid
        ? `Passed · ${status.bytesRead} bytes`
        : "Not verified",
      tone: toneIf(Boolean(status.executableHeaderValid), "green", "yellow"),
      critical: true,
    },
    {
      title: "Entity map",
      status:
        status.entityMapStatus === "matched"
          ? status.entityMapProfileId ?? "matched"
          : status.entityMapStatus ?? "Not checked",
      tone: toneIf(status.entityMapStatus === "matched", "green", "yellow"),
      critical: true,
    },
    {
      title: "Mapping schema",
      status: `v${status.mappingSchemaVersion ?? 2}`,
      tone: "green",
    },
    {
      title: "Pointer validation",
      status: status.pointerValidation?.replaceAll("_", " ") ?? "Not run",
      tone:
        status.pointerValidation === "passed"
          ? "green"
          : status.pointerValidation === "failed"
            ? "red"
            : "yellow",
      critical: true,
    },
    {
      title: "Parser status",
      status: readable(status.parserStatus),
      tone: toneIf(status.parserStatus === "ready", "green", "yellow"),
      critical: true,
    },
    {
      title: "Active save",
      status:
        status.saveDetected === true
          ? "Detected"
          : status.saveDetected === false
            ? "Not readable"
            : "Not checked",
      tone:
        status.saveDetected === true
          ? "green"
          : status.saveDetected === false
            ? "red"
            : "yellow",
      critical: true,
    },
    {
      title: "Manager registry",
      status: status.entityRoot ?? "Unavailable",
      tone: tonePresent(status.entityRoot),
      critical: true,
    },
    {
      title: "Active manager",
      status: status.savePointer ?? "Unavailable",
      tone: tonePresent(status.savePointer),
      critical: true,
    },
    {
      title: "Last sync",
      status: readable(status.lastSync),
      tone: tonePresent(status.lastSync),
    },
    {
      title: "Last successful read",
      status: readable(status.lastSuccessfulRead),
      tone: tonePresent(status.lastSuccessfulRead),
    },
    {
      title: "Failure stage",
      status: readable(status.failureStage),
      tone: status.failureStage ? "red" : "green",
      critical: true,
    },
    {
      title: "Data source",
      status: readable(snapshot.dataSource),
      tone: toneIf(snapshot.dataSource === "live-memory"),
    },
    {
      title: "Data error",
      status: snapshot.dataError?.trim() || "None",
      tone: snapshot.dataError?.trim() ? "red" : "green",
      critical: true,
    },
    {
      title: "FMT version",
      status: appVersion ?? "Unavailable",
      tone: tonePresent(appVersion),
    },
    {
      title: "Connector message",
      status: status.message?.trim() || "None",
      tone: "green",
      wide: true,
    },
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
    {
      title: "Manager name",
      status: snapshot.managerName ?? "Unavailable",
      tone: tonePresent(snapshot.managerName),
    },
    {
      title: "Manager pick",
      status: cellByTitle(backendCells, "Manager pick")?.status ?? "none",
      tone: cellByTitle(backendCells, "Manager pick")?.tone ?? "green",
    },
    {
      title: "Name fallback",
      status: cellByTitle(backendCells, "Name fallback")?.status ?? "none",
      tone: cellByTitle(backendCells, "Name fallback")?.tone ?? "green",
    },
  ];

  const teamCellsFromRoster: DiagCell[] = clubTeams.length
    ? clubTeams.map((team) => {
        const label = squadTeamDisplayName(team, managedClubName);
        const unit = team.squadUnit ?? "—";
        const type =
          typeof team.teamType === "number" ? `type=${team.teamType}` : "type=—";
        return {
          title: label,
          status: `uid ${team.teamUid} · ${unit} · ${team.rosterLen} roster · ${type}`,
          tone: team.rosterLen > 0 || team.isManagerTeam ? "green" : "yellow",
          critical: Boolean(team.isManagerTeam) && team.rosterLen === 0,
          wide: true,
        };
      })
    : [
        {
          title: "Club.Teams",
          status: "none",
          tone: "yellow" as const,
          critical: true,
          wide: true,
        },
      ];

  const teamsCells: DiagCell[] = [
    {
      title: "Squad collection",
      status: status.playerCollectionPointer ?? "Unavailable",
      tone: tonePresent(status.playerCollectionPointer),
      critical: true,
    },
    {
      title: "Load scope",
      status: status.databaseScope.replaceAll("-", " "),
      tone: toneIf(status.databaseScope !== "none", "green", "yellow"),
    },
    {
      title: "Clubs loaded",
      status: String(status.clubsLoaded),
      tone: tonePresent(status.clubsLoaded, { zeroOk: false }),
    },
    {
      title: "Club.Teams + affiliate players loaded",
      status:
        cellByTitle(backendCells, "Club.Teams + affiliate players loaded")?.status ?? "none",
      tone:
        cellByTitle(backendCells, "Club.Teams + affiliate players loaded")?.tone ?? "yellow",
    },
    {
      title: "Squad-tab affiliate clubs",
      status: cellByTitle(backendCells, "Squad-tab affiliate clubs")?.status ?? "none",
      tone: cellByTitle(backendCells, "Squad-tab affiliate clubs")?.tone ?? "yellow",
      wide: true,
    },
    ...teamCellsFromRoster,
  ];

  const playersCells: DiagCell[] = [
    {
      title: "Players loaded",
      status: String(status.playersLoaded),
      tone: tonePresent(status.playersLoaded, { zeroOk: false }),
      critical: true,
    },
    {
      title: "Squad players loaded",
      status: String(status.managedSquadPlayers),
      tone: tonePresent(status.managedSquadPlayers, { zeroOk: false }),
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
      title: "Visible players loaded",
      status: String(status.visiblePlayersLoaded),
      tone: tonePresent(status.visiblePlayersLoaded, { zeroOk: false }),
    },
    {
      title: "Fully scouted players",
      status: String(status.fullyScoutedPlayers),
      tone: tonePresent(status.fullyScoutedPlayers, { zeroOk: false }),
    },
    {
      title: "Partial scout reports",
      status: String(status.partialScoutReports),
      tone: tonePresent(status.partialScoutReports, { zeroOk: true, empty: "green" }),
    },
    {
      title: "Skipped squad slots",
      status: cellByTitle(backendCells, "Skipped squad slots")?.status ?? "none",
      tone: cellByTitle(backendCells, "Skipped squad slots")?.tone ?? "green",
      critical: true,
      wide: true,
    },
    {
      title: "Squad field coverage",
      status: cellByTitle(backendCells, "Squad field coverage")?.status ?? "none",
      tone: cellByTitle(backendCells, "Squad field coverage")?.tone ?? "yellow",
      wide: true,
    },
    {
      title: "Unvalidated fields",
      status: cellByTitle(backendCells, "Unvalidated fields")?.status ?? "none",
      tone: cellByTitle(backendCells, "Unvalidated fields")?.tone ?? "yellow",
      wide: true,
    },
    {
      title: "In-game date",
      status: snapshot.gameDate?.trim() || "Unavailable",
      tone: tonePresent(snapshot.gameDate),
      critical: true,
    },
    {
      title: "Season",
      status: snapshot.season?.trim() || "Unavailable",
      tone: tonePresent(snapshot.season),
    },
    {
      title: "Mapping coverage",
      status: mappingCoverageLabel(status.mappingCoverage),
      tone: (status.mappingCoverage ?? []).some((row) => row.unmapped > 0)
        ? "yellow"
        : tonePresent(mappingCoverageLabel(status.mappingCoverage), { empty: "yellow" }),
      wide: true,
    },
  ];

  const affiliationTitles = [
    "Affiliations club+0x118",
    "Unlabeled affiliation types",
    "Players Go On Loan filter",
    "Excluded affiliation links",
    "Dropped loan-off feeders",
    "Unresolved affiliate partners",
    "Affiliate clubs loaded",
    "Match experience affiliate teams",
  ];
  const affiliationsCells: DiagCell[] = affiliationTitles.map((title) => {
    const fromBackend = cellByTitle(backendCells, title);
    return {
      title,
      status: fromBackend?.status ?? "none",
      tone: fromBackend?.tone ?? "yellow",
      critical:
        title === "Unresolved affiliate partners" ||
        (title === "Affiliate clubs loaded" && fromBackend?.tone === "red"),
      wide: (fromBackend?.status.length ?? 0) > 80,
    };
  });

  const graphicsCells: DiagCell[] = [
    {
      title: "Graphics folder",
      status: graphics?.graphicsPath?.trim() || "Unavailable",
      tone: tonePresent(graphics?.graphicsPath, { empty: "yellow" }),
      wide: true,
    },
    {
      title: "Pack count",
      status:
        !graphics || graphics.loading
          ? "…"
          : String(graphics.packs.length),
      tone:
        !graphics || graphics.loading
          ? "yellow"
          : graphics.packs.length
            ? "green"
            : "yellow",
    },
    ...(!graphics || graphics.loading
      ? []
      : graphics.packs.length
        ? graphics.packs.map((pack) => {
            const path =
              pack.path?.trim() ||
              (graphics.graphicsPath
                ? `${graphics.graphicsPath.replace(/[\\/]+$/, "")}\\${pack.name}`
                : "Path unavailable");
            return {
              title: pack.name,
              status: `${pack.kind} · ${path}`,
              tone: path === "Path unavailable" ? ("yellow" as const) : ("green" as const),
              wide: true,
            };
          })
        : [
            {
              title: "Packs",
              status: "none",
              tone: "yellow" as const,
            },
          ]),
  ];

  const scoresCells: DiagCell[] = FRONTEND_CALCULATION_CARDS.map((calc) => ({
    title: calc.title,
    status: `${calc.badge} · ${calc.detail}`,
    tone: calc.state === "passed" ? "green" : calc.state === "blocked" ? "red" : "yellow",
    wide: true,
  }));

  const scoresLive = FRONTEND_CALCULATION_CARDS.filter((c) => c.state === "passed").length;

  return (
    <main className="screen settings-screen">
      <div className="planner-heading">
        <div>
          <h1>Settings</h1>
          <p>
            Diagnostics for the live FM26 read.
            {appVersion ? ` · FMT ${appVersion}` : null}
          </p>
        </div>
      </div>

      <section className="settings-list">
        <SettingsGroup
          id="settings-fm26"
          icon={<Gamepad2 aria-hidden="true" />}
          title="FM26"
          subtitle={
            status.processDetected ? "Football Manager 26 detected" : "Waiting for FM26"
          }
          meta={memorySafetyLabel(status.memoryAccess)}
          tone={sectionTone(fm26Cells)}
          cells={fm26Cells}
          action={
            <Button variant="outline" onClick={onRefresh} disabled={checking}>
              <RefreshCw
                data-icon="inline-start"
                className={checking ? "spin" : undefined}
              />
              Load Active Save
            </Button>
          }
        />

        <SettingsGroup
          id="settings-club"
          icon={<Building2 aria-hidden="true" />}
          title="Club"
          subtitle={managedClubName ?? "Managed club"}
          meta={snapshot.managedClubId ?? "—"}
          tone={sectionTone(clubCells)}
          cells={clubCells}
        />

        <SettingsGroup
          id="settings-teams"
          icon={<Users aria-hidden="true" />}
          title="Teams"
          subtitle="Club.Teams"
          meta={clubTeams.length ? `${clubTeams.length} teams` : "—"}
          tone={sectionTone(teamsCells)}
          cells={teamsCells}
        />

        <SettingsGroup
          id="settings-players"
          icon={<UserRound aria-hidden="true" />}
          title="Players"
          subtitle="Rosters and mapped fields"
          meta={status.playersLoaded ? `${status.playersLoaded} loaded` : "—"}
          tone={sectionTone(playersCells)}
          cells={playersCells}
        />

        <SettingsGroup
          id="settings-affiliations"
          icon={<Network aria-hidden="true" />}
          title="Affiliations"
          subtitle="club+0x118"
          meta={
            cellByTitle(backendCells, "Affiliate clubs loaded")?.status &&
            cellByTitle(backendCells, "Affiliate clubs loaded")?.status !== "none"
              ? "loaded"
              : "—"
          }
          tone={sectionTone(affiliationsCells)}
          cells={affiliationsCells}
        />

        <SettingsGroup
          id="settings-graphics"
          icon={<Images aria-hidden="true" />}
          title="Graphics"
          subtitle="Faces and logos"
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
          id="settings-scores"
          icon={<Sigma aria-hidden="true" />}
          title="Scores"
          subtitle="FMT calculations from mapped fields"
          meta={`${scoresLive} live`}
          tone={sectionTone(scoresCells)}
          cells={scoresCells}
        />
      </section>
    </main>
  );
}
