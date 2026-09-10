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
import {
  GraphicsPacksBody,
  useGraphicsPacksStatus,
} from "@/components/graphics-packs-panel";
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
  children,
  diagnostics,
}: {
  id: string;
  icon: ReactNode;
  title: string;
  subtitle: string;
  meta: string;
  tone: DiagnosticTone;
  children?: ReactNode;
  diagnostics: DiagCell[];
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
        {children}
        <div className="settings-diagnostics">
          <h3>Diagnostics</h3>
          <dl>
            {diagnostics.map((cell) => (
              <DiagnosticCellView key={cell.title} {...cell} />
            ))}
          </dl>
        </div>
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
  const connected =
    snapshot.status.state === "connected" && Boolean(snapshot.managedClubId);

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

  const fm26Diagnostics: DiagCell[] = [
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
      title: "Read-only access flags",
      status: status.handleAccessFlags ?? "Unavailable",
      tone: tonePresent(status.handleAccessFlags),
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

  const clubDiagnostics: DiagCell[] = [
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

  const teamsDiagnostics: DiagCell[] = [
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
      title: "Club.Teams discovered",
      status: cellByTitle(backendCells, "Club.Teams discovered")?.status ?? "none",
      tone: cellByTitle(backendCells, "Club.Teams discovered")?.tone ?? "yellow",
      critical: true,
      wide: true,
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
    },
  ];

  const playersDiagnostics: DiagCell[] = [
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
  const affiliationsDiagnostics: DiagCell[] = affiliationTitles.map((title) => {
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

  const graphicsDiagnostics: DiagCell[] = [
    {
      title: "Graphics folder",
      status: graphics?.graphicsPath?.trim() || "Unavailable",
      tone: tonePresent(graphics?.graphicsPath, { empty: "yellow" }),
      wide: true,
    },
    {
      title: "Packs",
      status:
        !graphics || graphics.loading
          ? "…"
          : graphics.packs.length
            ? `${graphics.packs.length}`
            : "none",
      tone:
        !graphics || graphics.loading
          ? "yellow"
          : graphics.packs.length
            ? "green"
            : "yellow",
    },
  ];

  const scoresDiagnostics: DiagCell[] = FRONTEND_CALCULATION_CARDS.map((calc) => ({
    title: calc.title,
    status: calc.detail,
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
            FM26 connector and local controls.
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
          tone={sectionTone(fm26Diagnostics)}
          diagnostics={fm26Diagnostics}
        >
          <div className="settings-expand-actions">
            <Button variant="outline" onClick={onRefresh} disabled={checking}>
              <RefreshCw
                data-icon="inline-start"
                className={checking ? "spin" : undefined}
              />
              Load Active Save
            </Button>
          </div>
          <p className="settings-group-note">
            Query and read access only. FMT cannot write to FM26.
          </p>
        </SettingsGroup>

        <SettingsGroup
          id="settings-club"
          icon={<Building2 aria-hidden="true" />}
          title="Club"
          subtitle={managedClubName ?? "Managed club"}
          meta={snapshot.managedClubId ?? "—"}
          tone={sectionTone(clubDiagnostics)}
          diagnostics={clubDiagnostics}
        />

        <SettingsGroup
          id="settings-teams"
          icon={<Users aria-hidden="true" />}
          title="Teams"
          subtitle="Club.Teams roster lengths"
          meta={connected && clubTeams.length ? `${clubTeams.length} teams` : "—"}
          tone={sectionTone(teamsDiagnostics)}
          diagnostics={teamsDiagnostics}
        >
          {connected && clubTeams.length ? (
            <dl className="settings-club-roster-lens">
              {clubTeams.map((team) => (
                <div key={team.teamUid}>
                  <dt>{squadTeamDisplayName(team, managedClubName)}</dt>
                  <dd>{team.rosterLen}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="settings-club-roster-empty">
              Load an active save to see Club.Teams rosterLen values.
            </p>
          )}
        </SettingsGroup>

        <SettingsGroup
          id="settings-players"
          icon={<UserRound aria-hidden="true" />}
          title="Players"
          subtitle="Rosters and mapped fields"
          meta={
            status.playersLoaded
              ? `${status.playersLoaded} loaded`
              : "—"
          }
          tone={sectionTone(playersDiagnostics)}
          diagnostics={playersDiagnostics}
        />

        <SettingsGroup
          id="settings-affiliations"
          icon={<Network aria-hidden="true" />}
          title="Affiliations"
          subtitle="club+0x118 feeders, II, Match experience"
          meta={
            cellByTitle(backendCells, "Affiliate clubs loaded")?.status &&
            cellByTitle(backendCells, "Affiliate clubs loaded")?.status !== "none"
              ? "loaded"
              : "—"
          }
          tone={sectionTone(affiliationsDiagnostics)}
          diagnostics={affiliationsDiagnostics}
        />

        <SettingsGroup
          id="settings-graphics"
          icon={<Images aria-hidden="true" />}
          title="Graphics"
          subtitle="Faces and logos from the FM26 graphics folder"
          meta={
            !graphics || graphics.loading
              ? "…"
              : graphics.packs.length
                ? `${graphics.packs.length} packs`
                : "None"
          }
          tone={sectionTone(graphicsDiagnostics)}
          diagnostics={graphicsDiagnostics}
        >
          <GraphicsPacksBody status={graphics} />
        </SettingsGroup>

        <SettingsGroup
          id="settings-scores"
          icon={<Sigma aria-hidden="true" />}
          title="Scores"
          subtitle="FMT calculations from mapped fields"
          meta={`${scoresLive} live`}
          tone={sectionTone(scoresDiagnostics)}
          diagnostics={scoresDiagnostics}
        >
          <div className="read-pipeline-grid">
            {FRONTEND_CALCULATION_CARDS.map((calc) => (
              <article key={calc.key} data-state={calc.state}>
                <span>{calc.badge}</span>
                <strong>{calc.title}</strong>
                <p>{calc.detail}</p>
              </article>
            ))}
          </div>
        </SettingsGroup>
      </section>
    </main>
  );
}
