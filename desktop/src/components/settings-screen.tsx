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

        <details className="advanced-diagnostics">
        <summary><span><Cpu />Advanced diagnostics</span><ChevronDown /></summary>
        <p>Technical connection details for troubleshooting supported FM26 builds.</p>
        <dl>
          <div><dt>Process</dt><dd>{status.processDetected ? `Detected · PID ${status.processId}` : "Not detected"}</dd></div>
          <div><dt>Executable</dt><dd>{status.processPath ?? "Unavailable"}</dd></div>
          <div><dt>FM26 build</dt><dd>{status.gameBuild ?? "Unavailable"}</dd></div>
          <div><dt>Product version</dt><dd>{status.productVersion ?? "Unavailable"}</dd></div>
          <div><dt>Architecture</dt><dd>{status.architecture ?? "Unavailable"}</dd></div>
          <div><dt>Module base</dt><dd>{status.moduleBase ?? "Unavailable"}</dd></div>
          <div><dt>Memory probe</dt><dd>{status.executableHeaderValid ? `Passed · ${status.bytesRead} bytes` : "Not verified"}</dd></div>
          <div><dt>Entity map</dt><dd>{status.entityMapStatus === "matched" ? status.entityMapProfileId : status.entityMapStatus ?? "Not checked"}</dd></div>
          <div><dt>Mapping schema</dt><dd>v{status.mappingSchemaVersion ?? 2}</dd></div>
          <div><dt>Pointer validation</dt><dd>{status.pointerValidation?.replaceAll("_", " ") ?? "Not run"}</dd></div>
          <div><dt>Active save</dt><dd>{status.saveDetected === true ? "Detected" : "Not readable"}</dd></div>
          <div><dt>Read-only access flags</dt><dd>{status.handleAccessFlags ?? "Unavailable"}</dd></div>
          <div><dt>Manager registry</dt><dd>{status.entityRoot ?? "Unavailable"}</dd></div>
          <div><dt>Active manager</dt><dd>{status.savePointer ?? "Unavailable"}</dd></div>
          <div><dt>Managed club</dt><dd>{status.managedClubPointer ?? "Unavailable"}</dd></div>
          <div><dt>Squad collection</dt><dd>{status.playerCollectionPointer ?? "Unavailable"}</dd></div>
          <div><dt>Load scope</dt><dd>{status.databaseScope.replaceAll("-", " ")}</dd></div>
          <div><dt>Squad players loaded</dt><dd>{status.managedSquadPlayers}</dd></div>
          <div><dt>Club employees</dt><dd>{status.clubEmployees || status.managedSquadPlayers}</dd></div>
          <div><dt>Last successful read</dt><dd>{readable(status.lastSuccessfulRead)}</dd></div>
          <div><dt>Failure stage</dt><dd>{readable(status.failureStage)}</dd></div>
          <div><dt>Windows error</dt><dd>{status.windowsErrorCode ?? "None"}</dd></div>
          <div className="diagnostic-hash"><dt>Executable SHA-256</dt><dd>{status.executableSha256 ?? "Unavailable"}</dd></div>
        </dl>
        <div className="advanced-diagnostic-message"><strong>Connector result</strong><span>{status.message}</span></div>
      </details>
    </main>
  );
}
