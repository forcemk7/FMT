"use client";

import { ChevronDown, Cpu, Database, GitBranch, LockKeyhole, RefreshCw, Sigma, Users } from "lucide-react";
import type { LiveFootballSnapshot } from "@/domain/adapters";
import { FRONTEND_CALCULATION_CARDS } from "@/domain/has-score";
import { sortClubTeamsForSquadDesk, squadTeamDisplayName } from "@/domain/live-data";
import { Button } from "@/components/ui/button";
import { GraphicsPacksPanel } from "@/components/graphics-packs-panel";
import { getVersion } from "@tauri-apps/api/app";
import { useEffect, useMemo, useState } from "react";

function readable(value: string | null | undefined) {
  if (!value) return "None";
  return value.replaceAll("_", " ").replaceAll("-", " ");
}

function stageLabel(state: string) {
  if (state === "passed") return "Passed";
  if (state === "warning") return "Needs mapping";
  if (state === "blocked") return "Blocked";
  return "Pending";
}

function pipelineSummary(pipeline: NonNullable<LiveFootballSnapshot["status"]["readPipeline"]>) {
  if (!pipeline.length) return "Not run";
  const passed = pipeline.filter((stage) => stage.state === "passed").length;
  return `${passed}/${pipeline.length} passed`;
}

function frontendCalculationsSummary() {
  const live = FRONTEND_CALCULATION_CARDS.filter((card) => card.state === "passed").length;
  return `${live} live`;
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

function DiagnosticCellView({
  title,
  status,
  tone,
  wide,
}: {
  title: string;
  status: string;
  tone: DiagnosticTone;
  wide?: boolean;
}) {
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
  const pipeline = status.readPipeline ?? [];
  const [appVersion, setAppVersion] = useState<string | null>(null);
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

  useEffect(() => {
    if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) return;
    getVersion().then(setAppVersion).catch(() => setAppVersion(null));
  }, []);

  return (
    <main className="screen settings-screen">
      <div className="planner-heading">
        <div>
          <h1>Settings</h1>
          <p>
            Live FM26 connector and local application controls.
            {appVersion ? ` · FMT ${appVersion}` : null}
          </p>
        </div>
      </div>
      <section className="settings-list">
        <article><Database /><div><strong>Active FM26 game</strong><span>{status.processDetected ? "Football Manager 26 detected" : "Waiting for FM26"}</span></div><Button variant="outline" onClick={onRefresh} disabled={checking}><RefreshCw data-icon="inline-start" className={checking ? "spin" : undefined} />Load Active Save</Button></article>
        <article>
          <LockKeyhole />
          <div>
            <strong>Memory safety</strong>
            <span>Query and read access only. FMT cannot write to FM26.</span>
          </div>
          <b>{memorySafetyLabel(status.memoryAccess)}</b>
        </article>
        <GraphicsPacksPanel />

        <details className="settings-expand" id="backend-read-pipeline">
          <summary>
            <GitBranch aria-hidden="true" />
            <div>
              <strong>Backend read pipeline</strong>
              <span>FM26 memory read stages</span>
            </div>
            <span className="settings-expand-meta">
              <b>{pipelineSummary(pipeline)}</b>
              <ChevronDown className="settings-expand-chevron" aria-hidden="true" />
            </span>
          </summary>
          <div className="settings-expand-body">
            <div className="read-pipeline-grid">
              {pipeline.length ? pipeline.map((stage) => (
                <article key={stage.key} data-state={stage.state}>
                  <span>{stageLabel(stage.state)}</span>
                  <strong>{stage.label}</strong>
                  <p>{stage.detail}</p>
                </article>
              )) : (
                <article data-state="pending">
                  <span>Pending</span>
                  <strong>Compact squad load</strong>
                  <p>Run the active-save read to load managed-club squads from live memory.</p>
                </article>
              )}
            </div>
          </div>
        </details>

        <details className="settings-expand" id="frontend-calculations">
          <summary>
            <Sigma aria-hidden="true" />
            <div>
              <strong>Frontend calculations</strong>
              <span>FMT scores from mapped fields</span>
            </div>
            <span className="settings-expand-meta">
              <b>{frontendCalculationsSummary()}</b>
              <ChevronDown className="settings-expand-chevron" aria-hidden="true" />
            </span>
          </summary>
          <div className="settings-expand-body">
            <div className="read-pipeline-grid">
              {FRONTEND_CALCULATION_CARDS.map((calc) => (
                <article key={calc.key} data-state={calc.state}>
                  <span>{calc.badge}</span>
                  <strong>{calc.title}</strong>
                  <p>{calc.detail}</p>
                </article>
              ))}
            </div>
          </div>
        </details>

        <details className="settings-expand" id="club-team-roster-lens">
          <summary>
            <Users aria-hidden="true" />
            <div>
              <strong>Club team roster lengths</strong>
              <span>FM vector rosterLen per Club.Teams entry (dev)</span>
            </div>
            <span className="settings-expand-meta">
              <b>{connected && clubTeams.length ? `${clubTeams.length} teams` : "—"}</b>
              <ChevronDown className="settings-expand-chevron" aria-hidden="true" />
            </span>
          </summary>
          <div className="settings-expand-body">
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
          </div>
        </details>
      </section>

      <details className="diagnostics">
        <summary>
          <span>
            <Cpu />
            Diagnostics
          </span>
          <ChevronDown />
        </summary>
        <p>Connection and load values collected during the live FM26 read, in load order.</p>
        <dl>
          <DiagnosticCellView
            title="Connection state"
            status={readable(status.state)}
            tone={toneIf(status.state === "connected")}
          />
          <DiagnosticCellView
            title="Process"
            status={status.processDetected ? `Detected · PID ${status.processId}` : "Not detected"}
            tone={toneIf(Boolean(status.processDetected))}
          />
          <DiagnosticCellView
            title="Executable"
            status={status.processPath ?? "Unavailable"}
            tone={tonePresent(status.processPath)}
          />
          <DiagnosticCellView
            title="Memory access"
            status={readable(status.memoryAccess)}
            tone={toneIf(status.memoryAccess.includes("read"), "green", "red")}
          />
          <DiagnosticCellView
            title="Can write memory"
            status={status.canWriteMemory ? "Yes" : "No"}
            tone="green"
          />
          <DiagnosticCellView
            title="Read-only access flags"
            status={status.handleAccessFlags ?? "Unavailable"}
            tone={tonePresent(status.handleAccessFlags)}
          />
          <DiagnosticCellView
            title="Windows error"
            status={status.windowsErrorCode != null ? String(status.windowsErrorCode) : "None"}
            tone={status.windowsErrorCode != null ? "red" : "green"}
          />
          <DiagnosticCellView
            title="FM26 build"
            status={status.gameBuild ?? "Unavailable"}
            tone={tonePresent(status.gameBuild)}
          />
          <DiagnosticCellView
            title="Product version"
            status={status.productVersion ?? "Unavailable"}
            tone={tonePresent(status.productVersion)}
          />
          <DiagnosticCellView
            title="Architecture"
            status={status.architecture ?? "Unavailable"}
            tone={tonePresent(status.architecture)}
          />
          <DiagnosticCellView
            title="Executable SHA-256"
            status={status.executableSha256 ?? "Unavailable"}
            tone={tonePresent(status.executableSha256)}
            wide
          />
          <DiagnosticCellView
            title="Module base"
            status={status.moduleBase ?? "Unavailable"}
            tone={tonePresent(status.moduleBase)}
          />
          <DiagnosticCellView
            title="Memory probe"
            status={
              status.executableHeaderValid ? `Passed · ${status.bytesRead} bytes` : "Not verified"
            }
            tone={toneIf(Boolean(status.executableHeaderValid), "green", "yellow")}
          />
          <DiagnosticCellView
            title="Entity map"
            status={
              status.entityMapStatus === "matched"
                ? status.entityMapProfileId ?? "matched"
                : status.entityMapStatus ?? "Not checked"
            }
            tone={toneIf(status.entityMapStatus === "matched", "green", "yellow")}
          />
          <DiagnosticCellView
            title="Mapping schema"
            status={`v${status.mappingSchemaVersion ?? 2}`}
            tone="green"
          />
          <DiagnosticCellView
            title="Mapping coverage"
            status={mappingCoverageLabel(status.mappingCoverage)}
            tone={
              (status.mappingCoverage ?? []).some((row) => row.unmapped > 0)
                ? "yellow"
                : tonePresent(mappingCoverageLabel(status.mappingCoverage), { empty: "yellow" })
            }
            wide
          />
          <DiagnosticCellView
            title="Pointer validation"
            status={status.pointerValidation?.replaceAll("_", " ") ?? "Not run"}
            tone={
              status.pointerValidation === "passed"
                ? "green"
                : status.pointerValidation === "failed"
                  ? "red"
                  : "yellow"
            }
          />
          <DiagnosticCellView
            title="Parser status"
            status={readable(status.parserStatus)}
            tone={toneIf(status.parserStatus === "ready", "green", "yellow")}
          />
          <DiagnosticCellView
            title="Active save"
            status={
              status.saveDetected === true
                ? "Detected"
                : status.saveDetected === false
                  ? "Not readable"
                  : "Not checked"
            }
            tone={
              status.saveDetected === true
                ? "green"
                : status.saveDetected === false
                  ? "red"
                  : "yellow"
            }
          />
          <DiagnosticCellView
            title="Manager registry"
            status={status.entityRoot ?? "Unavailable"}
            tone={tonePresent(status.entityRoot)}
          />
          <DiagnosticCellView
            title="Active manager"
            status={status.savePointer ?? "Unavailable"}
            tone={tonePresent(status.savePointer)}
          />
          <DiagnosticCellView
            title="Managed club pointer"
            status={status.managedClubPointer ?? "Unavailable"}
            tone={tonePresent(status.managedClubPointer)}
          />
          <DiagnosticCellView
            title="Squad collection"
            status={status.playerCollectionPointer ?? "Unavailable"}
            tone={tonePresent(status.playerCollectionPointer)}
          />
          <DiagnosticCellView
            title="Managed club id"
            status={snapshot.managedClubId ?? "Unavailable"}
            tone={tonePresent(snapshot.managedClubId)}
          />
          <DiagnosticCellView
            title="Managed club name"
            status={managedClubName ?? "Unavailable"}
            tone={tonePresent(managedClubName)}
          />
          <DiagnosticCellView
            title="Manager name"
            status={snapshot.managerName ?? "Unavailable"}
            tone={tonePresent(snapshot.managerName)}
          />
          <DiagnosticCellView
            title="Load scope"
            status={status.databaseScope.replaceAll("-", " ")}
            tone={toneIf(status.databaseScope !== "none", "green", "yellow")}
          />
          <DiagnosticCellView
            title="Players loaded"
            status={String(status.playersLoaded)}
            tone={tonePresent(status.playersLoaded, { zeroOk: false })}
          />
          <DiagnosticCellView
            title="Squad players loaded"
            status={String(status.managedSquadPlayers)}
            tone={tonePresent(status.managedSquadPlayers, { zeroOk: false })}
          />
          <DiagnosticCellView
            title="Club employees"
            status={String(status.clubEmployees || status.managedSquadPlayers)}
            tone={tonePresent(status.clubEmployees || status.managedSquadPlayers, { zeroOk: false })}
          />
          <DiagnosticCellView
            title="Visible players loaded"
            status={String(status.visiblePlayersLoaded)}
            tone={tonePresent(status.visiblePlayersLoaded, { zeroOk: false })}
          />
          <DiagnosticCellView
            title="Clubs loaded"
            status={String(status.clubsLoaded)}
            tone={tonePresent(status.clubsLoaded, { zeroOk: false })}
          />
          <DiagnosticCellView
            title="Database index status"
            status={readable(status.databaseIndexStatus)}
            tone={toneIf(status.databaseIndexStatus !== "not_run", "green", "yellow")}
          />
          <DiagnosticCellView
            title="Database players indexed"
            status={String(status.databasePlayersIndexed)}
            tone={tonePresent(status.databasePlayersIndexed, { zeroOk: true, empty: "green" })}
          />
          <DiagnosticCellView
            title="Background players indexed"
            status={String(status.backgroundPlayersIndexed)}
            tone={tonePresent(status.backgroundPlayersIndexed, { zeroOk: true, empty: "green" })}
          />
          <DiagnosticCellView
            title="Fully scouted players"
            status={String(status.fullyScoutedPlayers)}
            tone={tonePresent(status.fullyScoutedPlayers, { zeroOk: false })}
          />
          <DiagnosticCellView
            title="Partial scout reports"
            status={String(status.partialScoutReports)}
            tone={tonePresent(status.partialScoutReports, { zeroOk: true, empty: "green" })}
          />
          {(status.diagnosticCells ?? []).map((cell) => (
            <DiagnosticCellView
              key={cell.title}
              title={cell.title}
              status={cell.status}
              tone={cell.tone ?? "yellow"}
              wide={cell.status.length > 80}
            />
          ))}
          <DiagnosticCellView
            title="In-game date"
            status={snapshot.gameDate?.trim() || "Unavailable"}
            tone={tonePresent(snapshot.gameDate)}
          />
          <DiagnosticCellView
            title="Season"
            status={snapshot.season?.trim() || "Unavailable"}
            tone={tonePresent(snapshot.season)}
          />
          <DiagnosticCellView
            title="Live tactic read"
            status={readable(status.liveMemoryTacticRead)}
            tone={
              status.liveMemoryTacticRead === "ready"
                ? "green"
                : status.liveMemoryTacticRead === "object_not_found"
                  ? "yellow"
                  : "yellow"
            }
          />
          <DiagnosticCellView
            title="Tactic manager pointer"
            status={status.tacticManagerPointer ?? "Unavailable"}
            tone={tonePresent(status.tacticManagerPointer, { empty: "yellow" })}
          />
          <DiagnosticCellView
            title="Tactic source"
            status={readable(snapshot.tacticSource)}
            tone={toneIf(snapshot.tacticSource !== "none", "green", "yellow")}
          />
          <DiagnosticCellView
            title="Read pipeline"
            status={pipelineSummary(pipeline)}
            tone={toneIf(pipeline.length > 0 && pipeline.every((s) => s.state === "passed"), "green", "yellow")}
          />
          <DiagnosticCellView
            title="Last sync"
            status={readable(status.lastSync)}
            tone={tonePresent(status.lastSync)}
          />
          <DiagnosticCellView
            title="Last successful read"
            status={readable(status.lastSuccessfulRead)}
            tone={tonePresent(status.lastSuccessfulRead)}
          />
          <DiagnosticCellView
            title="Failure stage"
            status={readable(status.failureStage)}
            tone={status.failureStage ? "red" : "green"}
          />
          <DiagnosticCellView
            title="Data source"
            status={readable(snapshot.dataSource)}
            tone={toneIf(snapshot.dataSource === "live-memory")}
          />
          <DiagnosticCellView
            title="Data error"
            status={snapshot.dataError?.trim() || "None"}
            tone={snapshot.dataError?.trim() ? "red" : "green"}
          />
        </dl>
        <div className="diagnostic-message">
          <strong>Connector result</strong>
          <span>{status.message}</span>
        </div>
      </details>
    </main>
  );
}

