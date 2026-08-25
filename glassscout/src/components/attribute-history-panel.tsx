"use client";

import { useMemo, useState } from "react";
import {
  colorForSeries,
  fieldDeltas,
  formatDelta,
  getPlayerAttrHistory,
  type AttrHistoryPoint,
} from "@/domain/attribute-history";

const DEFAULT_FIELDS = ["CA", "PA", "Determination", "Professionalism", "Consistency"];

function smoothLinePath(pts: Array<{ x: number; y: number }>): string {
  if (pts.length === 0) return "";
  if (pts.length === 1) return `M ${pts[0]!.x} ${pts[0]!.y}`;
  if (pts.length === 2) return `M ${pts[0]!.x} ${pts[0]!.y} L ${pts[1]!.x} ${pts[1]!.y}`;
  let d = `M ${pts[0]!.x} ${pts[0]!.y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i]!;
    const p1 = pts[i]!;
    const p2 = pts[i + 1]!;
    const p3 = pts[i + 2] ?? p2;
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${c1x} ${c1y} ${c2x} ${c2y} ${p2.x} ${p2.y}`;
  }
  return d;
}

function availableFields(points: AttrHistoryPoint[]): string[] {
  const keys = new Set<string>();
  for (const point of points) {
    for (const key of Object.keys(point.values)) keys.add(key);
  }
  return [...keys].sort((a, b) => a.localeCompare(b));
}

export function AttributeHistoryPanel({ playerId }: { playerId: string }) {
  const points = getPlayerAttrHistory(playerId);
  const fields = availableFields(points);
  // null = use defaults; remount via key={playerId} resets. No useEffect → no update loops.
  const [active, setActive] = useState<string[] | null>(null);
  const selected =
    active === null
      ? DEFAULT_FIELDS.filter((field) => fields.includes(field)).slice(0, 3)
      : active.filter((field) => fields.includes(field));

  const selectedKey = selected.join("\0");
  const chart = useMemo(() => {
    if (points.length === 0 || selected.length === 0) return null;
    const width = 640;
    const height = 220;
    const pad = { left: 36, right: 12, top: 16, bottom: 28 };
    const innerW = width - pad.left - pad.right;
    const innerH = height - pad.top - pad.bottom;
    let yMin = Infinity;
    let yMax = -Infinity;
    for (const field of selected) {
      for (const point of points) {
        const value = point.values[field];
        if (typeof value !== "number") continue;
        yMin = Math.min(yMin, value);
        yMax = Math.max(yMax, value);
      }
    }
    if (!Number.isFinite(yMin) || !Number.isFinite(yMax)) return null;
    if (yMin === yMax) {
      yMin -= 1;
      yMax += 1;
    }
    const xAt = (index: number) =>
      pad.left + (points.length <= 1 ? innerW / 2 : (index / (points.length - 1)) * innerW);
    const yAt = (value: number) => pad.top + ((yMax - value) / (yMax - yMin)) * innerH;

    const series = selected.map((field, index) => {
      const pts = points.flatMap((point, pointIndex) => {
        const value = point.values[field];
        if (typeof value !== "number") return [];
        return [{ x: xAt(pointIndex), y: yAt(value) }];
      });
      return { field, color: colorForSeries(index), path: smoothLinePath(pts), pts };
    });

    return { width, height, pad, yMin, yMax, series };
  }, [playerId, points.length, selectedKey]);

  const toggle = (field: string) => {
    setActive((current) => {
      const base =
        current ?? DEFAULT_FIELDS.filter((item) => fields.includes(item)).slice(0, 3);
      return base.includes(field) ? base.filter((item) => item !== field) : [...base, field];
    });
  };

  if (points.length === 0) {
    return (
      <section className="dossier-panel tab-evidence-panel attr-history-panel">
        <header><h2>Attribute history</h2><span>No change-points yet</span></header>
        <p className="evidence-caption">
          History appends on each Load Active Save when values change. Reload after development days to build the plot.
        </p>
      </section>
    );
  }

  return (
    <section className="dossier-panel tab-evidence-panel attr-history-panel">
      <header>
        <h2>Attribute history</h2>
        <span>{points.length} change-point{points.length === 1 ? "" : "s"} · append-only</span>
      </header>
      <div className="attr-history-layout">
        <div className="attr-history-toggles">
          {fields.map((field) => {
            const on = selected.includes(field);
            const deltas = fieldDeltas(points, field);
            return (
              <button
                key={field}
                type="button"
                className={on ? "is-on" : undefined}
                onClick={() => toggle(field)}
              >
                <strong>{field}</strong>
                <small>
                  {deltas.latest ?? "—"} · Δr {formatDelta(deltas.recent)} · Δ∞ {formatDelta(deltas.allTime)}
                </small>
              </button>
            );
          })}
        </div>
        <div className="attr-history-chart">
          {chart ? (
            <svg viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label="Attribute history plot">
              <text x={8} y={chart.pad.top + 4} className="attr-history-axis">{Math.round(chart.yMax)}</text>
              <text x={8} y={chart.height - chart.pad.bottom} className="attr-history-axis">{Math.round(chart.yMin)}</text>
              {chart.series.map((series) => (
                <g key={series.field}>
                  <path d={series.path} fill="none" stroke={series.color} strokeWidth={2} />
                  {series.pts.map((pt, index) => (
                    <circle key={`${series.field}-${index}`} cx={pt.x} cy={pt.y} r={3} fill={series.color} />
                  ))}
                </g>
              ))}
              <text x={chart.width / 2} y={chart.height - 6} textAnchor="middle" className="attr-history-axis">
                change-points (not calendar)
              </text>
            </svg>
          ) : (
            <p className="evidence-caption">Toggle one or more fields to plot.</p>
          )}
        </div>
      </div>
      <p className="evidence-caption">
        Δr = vs previous point · Δ∞ = vs first point. Values are never overwritten.
      </p>
    </section>
  );
}
