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
          {/* 1. Process detect */}
          <div>
            <dt>Connection state</dt>
            <dd>{readable(status.state)}</dd>
          </div>
          <div>
            <dt>Process</dt>
            <dd>{status.processDetected ? `Detected · PID ${status.processId}` : "Not detected"}</dd>
          </div>
          <div>
            <dt>Executable</dt>
            <dd>{status.processPath ?? "Unavailable"}</dd>
          </div>
          {/* 2. Open handle / access */}
          <div>
            <dt>Memory access</dt>
            <dd>{readable(status.memoryAccess)}</dd>
          </div>
          <div>
            <dt>Can write memory</dt>
            <dd>{status.canWriteMemory ? "Yes" : "No"}</dd>
          </div>
          <div>
            <dt>Read-only access flags</dt>
            <dd>{status.handleAccessFlags ?? "Unavailable"}</dd>
          </div>
          <div>
            <dt>Windows error</dt>
            <dd>{status.windowsErrorCode ?? "None"}</dd>
          </div>
          {/* 3. Executable identity */}
          <div>
            <dt>FM26 build</dt>
            <dd>{status.gameBuild ?? "Unavailable"}</dd>
          </div>
          <div>
            <dt>Product version</dt>
            <dd>{status.productVersion ?? "Unavailable"}</dd>
          </div>
          <div>
            <dt>Architecture</dt>
            <dd>{status.architecture ?? "Unavailable"}</dd>
          </div>
          <div className="diagnostic-hash">
            <dt>Executable SHA-256</dt>
            <dd>{status.executableSha256 ?? "Unavailable"}</dd>
          </div>
          <div>
            <dt>Module base</dt>
            <dd>{status.moduleBase ?? "Unavailable"}</dd>
          </div>
          <div>
            <dt>Memory probe</dt>
            <dd>{status.executableHeaderValid ? `Passed · ${status.bytesRead} bytes` : "Not verified"}</dd>
          </div>
          {/* 4. Entity map */}
          <div>
            <dt>Entity map</dt>
            <dd>
              {status.entityMapStatus === "matched"
                ? status.entityMapProfileId
                : status.entityMapStatus ?? "Not checked"}
            </dd>
          </div>
          <div>
            <dt>Mapping schema</dt>
            <dd>v{status.mappingSchemaVersion ?? 2}</dd>
          </div>
          <div className="diagnostic-hash">
            <dt>Mapping coverage</dt>
            <dd>{mappingCoverageLabel(status.mappingCoverage)}</dd>
          </div>
          <div>
            <dt>Pointer validation</dt>
            <dd>{status.pointerValidation?.replaceAll("_", " ") ?? "Not run"}</dd>
          </div>
          <div>
            <dt>Parser status</dt>
            <dd>{readable(status.parserStatus)}</dd>
          </div>
          {/* 5. Manager / club / squad pointers */}
          <div>
            <dt>Active save</dt>
            <dd>{status.saveDetected === true ? "Detected" : status.saveDetected === false ? "Not readable" : "Not checked"}</dd>
          </div>
          <div>
            <dt>Manager registry</dt>
            <dd>{status.entityRoot ?? "Unavailable"}</dd>
          </div>
          <div>
            <dt>Active manager</dt>
            <dd>{status.savePointer ?? "Unavailable"}</dd>
          </div>
          <div>
            <dt>Managed club pointer</dt>
            <dd>{status.managedClubPointer ?? "Unavailable"}</dd>
          </div>
          <div>
            <dt>Squad collection</dt>
            <dd>{status.playerCollectionPointer ?? "Unavailable"}</dd>
          </div>
          {/* 6. Load results */}
          <div>
            <dt>Managed club id</dt>
            <dd>{snapshot.managedClubId ?? "Unavailable"}</dd>
          </div>
          <div>
            <dt>Managed club name</dt>
            <dd>{managedClubName ?? "Unavailable"}</dd>
          </div>
          <div>
            <dt>Manager name</dt>
            <dd>{snapshot.managerName ?? "Unavailable"}</dd>
          </div>
          <div>
            <dt>Load scope</dt>
            <dd>{status.databaseScope.replaceAll("-", " ")}</dd>
          </div>
          <div>
            <dt>Players loaded</dt>
            <dd>{status.playersLoaded}</dd>
          </div>
          <div>
            <dt>Squad players loaded</dt>
            <dd>{status.managedSquadPlayers}</dd>
          </div>
          <div>
            <dt>Club employees</dt>
            <dd>{status.clubEmployees || status.managedSquadPlayers}</dd>
          </div>
          <div>
            <dt>Visible players loaded</dt>
            <dd>{status.visiblePlayersLoaded}</dd>
          </div>
          <div>
            <dt>Clubs loaded</dt>
            <dd>{status.clubsLoaded}</dd>
          </div>
          <div>
            <dt>Database index status</dt>
            <dd>{readable(status.databaseIndexStatus)}</dd>
          </div>
          <div>
            <dt>Database players indexed</dt>
            <dd>{status.databasePlayersIndexed}</dd>
          </div>
          <div>
            <dt>Background players indexed</dt>
            <dd>{status.backgroundPlayersIndexed}</dd>
          </div>
          <div>
            <dt>Fully scouted players</dt>
            <dd>{status.fullyScoutedPlayers}</dd>
          </div>
          <div>
            <dt>Partial scout reports</dt>
            <dd>{status.partialScoutReports}</dd>
          </div>
          {(status.diagnosticCells ?? []).map((cell) => (
            <div
              key={cell.title}
              className={[
                cell.status.length > 80 ? "diagnostic-hash" : "",
                "diagnostic-cell",
                `tone-${cell.tone ?? "yellow"}`,
              ]
                .filter(Boolean)
                .join(" ")}
            >
              <dt>
                <span className="diagnostic-tone" aria-hidden="true" />
                {cell.title}
              </dt>
              <dd>{cell.status.trim() || "none"}</dd>
            </div>
          ))}
          {/* 7. In-game calendar (ages) */}
          <div>
            <dt>In-game date</dt>
            <dd>{snapshot.gameDate?.trim() || "Unavailable"}</dd>
          </div>
          <div>
            <dt>Season</dt>
            <dd>{snapshot.season?.trim() || "Unavailable"}</dd>
          </div>
          {/* 8. Tactic */}
          <div>
            <dt>Live tactic read</dt>
            <dd>{readable(status.liveMemoryTacticRead)}</dd>
          </div>
          <div>
            <dt>Tactic manager pointer</dt>
            <dd>{status.tacticManagerPointer ?? "Unavailable"}</dd>
          </div>
          <div>
            <dt>Tactic source</dt>
            <dd>{readable(snapshot.tacticSource)}</dd>
          </div>
          {/* 9. Outcome */}
          <div>
            <dt>Read pipeline</dt>
            <dd>{pipelineSummary(pipeline)}</dd>
          </div>
          <div>
            <dt>Last sync</dt>
            <dd>{readable(status.lastSync)}</dd>
          </div>
          <div>
            <dt>Last successful read</dt>
            <dd>{readable(status.lastSuccessfulRead)}</dd>
          </div>
          <div>
            <dt>Failure stage</dt>
            <dd>{readable(status.failureStage)}</dd>
          </div>
          <div>
            <dt>Data source</dt>
            <dd>{readable(snapshot.dataSource)}</dd>
          </div>
          <div>
            <dt>Data error</dt>
            <dd>{snapshot.dataError?.trim() || "None"}</dd>
          </div>
        </dl>
        <div className="diagnostic-message">
          <strong>Connector result</strong>
          <span>{status.message}</span>
        </div>
      </details>
    </main>
  );
}

