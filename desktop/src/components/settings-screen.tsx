"use client";

import { useEffect, useState } from "react";
import { ChevronDown, Cpu, Database, Image, LockKeyhole, RefreshCw } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import type { LiveFootballSnapshot } from "@/domain/adapters";
import { captureMappingEvidence, compareMappingEvidence, getMappingLabStatus, type MappingLabCaptureResult, type MappingLabComparisonResult, type MappingLabStatus } from "@/domain/adapters";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { clearPlayerFaceMemoryCache } from "@/components/player-face";

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

type GraphicsSettings = { graphicsRoots?: string[]; graphicsRoot?: string | null };
type FacesCacheStatus = {
  graphicsRoots?: Array<{ path: string; exists: boolean }>;
  graphicsRoot?: string;
  graphicsRootExists?: boolean;
  cacheDir: string;
  cachedFiles: number;
};
type FaceWarmResult = {
  requested: number;
  cached: number;
  copied: number;
  missing: number;
  graphicsRoots?: string[];
  graphicsRoot?: string;
  cacheDir: string;
};

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
  const [mappingLab, setMappingLab] = useState<MappingLabStatus | null>(null);
  const [mappingTarget, setMappingTarget] = useState("");
  const [mappingLabel, setMappingLabel] = useState("");
  const [capture, setCapture] = useState<MappingLabCaptureResult | null>(null);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [firstSnapshot, setFirstSnapshot] = useState("");
  const [secondSnapshot, setSecondSnapshot] = useState("");
  const [comparison, setComparison] = useState<MappingLabComparisonResult | null>(null);
  const [graphicsRootsText, setGraphicsRootsText] = useState("");
  const [faceStatus, setFaceStatus] = useState<FacesCacheStatus | null>(null);
  const [faceBusy, setFaceBusy] = useState(false);
  const [faceMessage, setFaceMessage] = useState<string | null>(null);

  const refreshFaceStatus = async () => {
    if (!("__TAURI_INTERNALS__" in window)) return;
    try {
      const [settings, cache] = await Promise.all([
        invoke<GraphicsSettings>("graphics_settings_get"),
        invoke<FacesCacheStatus>("faces_cache_status"),
      ]);
      const roots =
        settings.graphicsRoots?.filter(Boolean) ??
        (settings.graphicsRoot ? [settings.graphicsRoot] : []);
      setGraphicsRootsText(roots.join("\n"));
      setFaceStatus(cache);
    } catch {
      setFaceStatus(null);
    }
  };

  useEffect(() => {
    getMappingLabStatus().then(setMappingLab).catch(() => setMappingLab(null));
    void refreshFaceStatus();
  }, []);

  const captureEvidence = async () => {
    setCaptureError(null);
    try {
      setCapture(await captureMappingEvidence(mappingTarget, mappingLabel));
    } catch (error) {
      setCaptureError(error instanceof Error ? error.message : String(error));
    }
  };
  const compareEvidence = async () => {
    setCaptureError(null);
    try {
      setComparison(await compareMappingEvidence(firstSnapshot, secondSnapshot));
    } catch (error) {
      setCaptureError(error instanceof Error ? error.message : String(error));
    }
  };

  const parseRoots = () =>
    graphicsRootsText
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);

  const saveGraphicsPath = async () => {
    if (!("__TAURI_INTERNALS__" in window)) return;
    setFaceBusy(true);
    setFaceMessage(null);
    try {
      await invoke("graphics_settings_set", { graphicsRoots: parseRoots() });
      await refreshFaceStatus();
      setFaceMessage("Graphics folders saved.");
    } catch (error) {
      setFaceMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setFaceBusy(false);
    }
  };

  const updateFaces = async () => {
    if (!("__TAURI_INTERNALS__" in window)) return;
    setFaceBusy(true);
    setFaceMessage(null);
    try {
      await invoke("graphics_settings_set", { graphicsRoots: parseRoots() });
      const ids = snapshot.players.map((player) => player.id);
      const result = await invoke<FaceWarmResult>("faces_update_cache", { playerIds: ids });
      clearPlayerFaceMemoryCache();
      await refreshFaceStatus();
      setFaceMessage(
        ids.length
          ? `Faces: ${result.copied} copied, ${result.cached} already cached, ${result.missing} missing (of ${result.requested}).`
          : "Folders saved. Load a save first so Update can warm the squad; faces also copy on first view.",
      );
    } catch (error) {
      setFaceMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setFaceBusy(false);
    }
  };

  return (
    <main className="screen settings-screen">
      <div className="planner-heading">
        <div><h1>Settings</h1><p>Live FM26 connector and local application controls.</p></div>
      </div>
      <section className="settings-list">
        <article><Database /><div><strong>Active FM26 game</strong><span>{status.processDetected ? "Football Manager 26 detected" : "Waiting for FM26"}</span></div><Button variant="outline" onClick={onRefresh} disabled={checking}><RefreshCw data-icon="inline-start" className={checking ? "spin" : undefined} />Load Active Save</Button></article>
        <article><LockKeyhole /><div><strong>Memory safety</strong><span>Query and read access only. FMT cannot write to FM26.</span></div><b>{status.memoryAccess.replaceAll("_", " ")}</b></article>
      </section>

      <section className="settings-faces-panel">
        <header>
          <Image aria-hidden="true" />
          <div>
            <span className="section-kicker">Player faces</span>
            <h2>Cutout graphics</h2>
            <p>
              One folder per line — parent <code>graphics</code> and/or individual packs (Cutout,
              NewGAN). FMT checks all of them, then caches hits locally.
            </p>
          </div>
        </header>
        <label className="settings-faces-path">
          <span>Graphics folders</span>
          <textarea
            aria-label="FM26 graphics folders"
            className="settings-faces-roots"
            rows={3}
            value={graphicsRootsText}
            onChange={(event) => setGraphicsRootsText(event.target.value)}
            placeholder={"…\\Football Manager 26\\graphics\n…\\My NewGAN pack"}
          />
        </label>
        <div className="settings-faces-actions">
          <Button variant="outline" onClick={() => void saveGraphicsPath()} disabled={faceBusy}>
            Save folders
          </Button>
          <Button onClick={() => void updateFaces()} disabled={faceBusy}>
            <RefreshCw data-icon="inline-start" className={faceBusy ? "spin" : undefined} />
            Update faces
          </Button>
        </div>
        {faceStatus ? (
          <p className="evidence-caption">
            {(faceStatus.graphicsRoots ?? [])
              .map((root) => `${root.exists ? "ok" : "missing"}: ${root.path}`)
              .join(" · ") || "No roots"}{" "}
            · cache {faceStatus.cachedFiles} files
          </p>
        ) : (
          <p className="evidence-caption">Face settings available in the desktop app.</p>
        )}
        {faceMessage ? <p className="evidence-caption">{faceMessage}</p> : null}
      </section>

      <section className="read-pipeline-panel">
        <header>
          <div>
            <span className="section-kicker">Backend read pipeline</span>
            <h2>What FMT actually read from FM26</h2>
            <p>These stages come from the native connector. They separate live memory reads from still-unmapped fields and local enrichment.</p>
          </div>
          <Button variant="outline" onClick={onRefresh} disabled={checking}>
            <RefreshCw data-icon="inline-start" className={checking ? "spin" : undefined} />
            Re-run read
          </Button>
        </header>
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
              <strong>No pipeline yet</strong>
              <p>Run the active-save read to collect backend stage diagnostics.</p>
            </article>
          )}
        </div>
      </section>

      <details className="advanced-diagnostics">
        <summary><span><Cpu />Advanced diagnostics</span><ChevronDown /></summary>
        <p>Technical connection and visibility-gate details for troubleshooting supported FM26 builds.</p>
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
          <div><dt>Database index</dt><dd>{status.databaseIndexStatus.replaceAll("_", " ")}</dd></div>
          <div><dt>Database scope</dt><dd>{status.databaseScope.replaceAll("-", " ")}</dd></div>
          <div><dt>Managed squad players</dt><dd>{status.managedSquadPlayers}</dd></div>
          <div><dt>Player records indexed</dt><dd>{status.databasePlayersIndexed}</dd></div>
          <div><dt>Background records gated</dt><dd>{status.backgroundPlayersIndexed}</dd></div>
          <div><dt>Readable player profiles</dt><dd>{status.visiblePlayersLoaded}</dd></div>
          <div><dt>Fully scouted players</dt><dd>{status.fullyScoutedPlayers}</dd></div>
          <div><dt>Partial scout reports</dt><dd>{status.partialScoutReports}</dd></div>
          <div><dt>Live memory tactic read</dt><dd>{status.liveMemoryTacticRead ?? "disabled"}</dd></div>
          <div><dt>Tactic manager</dt><dd>{status.tacticManagerPointer ?? "Unavailable"}</dd></div>
          <div><dt>Tactic source</dt><dd>{snapshot.tacticSource.replaceAll("_", " ")}</dd></div>
          <div><dt>Last successful read</dt><dd>{readable(status.lastSuccessfulRead)}</dd></div>
          <div><dt>Failure stage</dt><dd>{readable(status.failureStage)}</dd></div>
          <div><dt>Windows error</dt><dd>{status.windowsErrorCode ?? "None"}</dd></div>
          <div className="diagnostic-hash"><dt>Executable SHA-256</dt><dd>{status.executableSha256 ?? "Unavailable"}</dd></div>
        </dl>
        <section className="mapping-coverage">
          <header><strong>Exact-build mapping coverage</strong><span>Only validated fields enter the live product.</span></header>
          {(status.mappingCoverage ?? []).map((item) => (
            <article key={item.section}>
              <strong>{item.section}</strong>
              <span className="coverage-good">{item.validated} validated</span>
              <span className="coverage-watch">{item.candidate} candidates</span>
              <span>{item.unmapped} unmapped</span>
            </article>
          ))}
        </section>
        {mappingLab?.enabled ? (
          <section className="mapping-lab-panel">
            <header><strong>Developer Mapping Lab</strong><span>Read-only · bounded to {mappingLab.maximumWindowBytes} bytes per object</span></header>
            <p>{mappingLab.message}</p>
            <div><Input aria-label="Mapping player" placeholder="Exact player name or FM ID" value={mappingTarget} onChange={(event) => setMappingTarget(event.target.value)} /><Input aria-label="Mapping evidence label" placeholder="Controlled state label" value={mappingLabel} onChange={(event) => setMappingLabel(event.target.value)} /><Button variant="outline" disabled={!mappingTarget.trim()} onClick={captureEvidence}>Capture local evidence</Button></div>
            {capture ? <small>Saved {capture.windowsCaptured} windows ({capture.bytesCaptured} bytes) to {capture.evidenceFile}</small> : null}
            <div><Input aria-label="First snapshot ID" placeholder="First snapshot ID" value={firstSnapshot} onChange={(event) => setFirstSnapshot(event.target.value)} /><Input aria-label="Second snapshot ID" placeholder="Second snapshot ID" value={secondSnapshot} onChange={(event) => setSecondSnapshot(event.target.value)} /><Button variant="outline" disabled={!firstSnapshot || !secondSnapshot} onClick={compareEvidence}>Compare snapshots</Button></div>
            {comparison ? <small>Diff: {comparison.changedBytes} changed, {comparison.unchangedBytes} unchanged bytes. Evidence: {comparison.evidenceFile}</small> : null}
            {captureError ? <small className="mapping-lab-error">{captureError}</small> : null}
          </section>
        ) : null}
        <div className="advanced-diagnostic-message"><strong>Connector result</strong><span>{status.message}</span></div>
      </details>
    </main>
  );
}
