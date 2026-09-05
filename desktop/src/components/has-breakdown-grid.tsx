import type { LivePlayer } from "@/domain/adapters";
import { liveHasBreakdown } from "@/domain/has-score";

export type HasBreakdownGridRow = {
  abbr: string;
  label?: string;
  value: string | number;
  tone: string;
};

export function HasBreakdownGrid({
  rows,
  ariaLabel,
  className,
}: {
  rows: HasBreakdownGridRow[];
  ariaLabel?: string;
  className?: string;
}) {
  if (!rows.length) return null;
  return (
    <div
      className={["dash-has-tooltip-grid", className].filter(Boolean).join(" ")}
      aria-label={ariaLabel}
    >
      {rows.map((row) => (
        <span
          key={row.abbr}
          className={`dash-has-tooltip-cell tone-${row.tone}`}
          title={row.label}
        >
          <small>{row.abbr}</small>
          <strong>{row.value}</strong>
        </span>
      ))}
    </div>
  );
}

export function HasBreakdownGridFromPlayer({ player }: { player: LivePlayer }) {
  const rows = liveHasBreakdown(player);
  return (
    <HasBreakdownGrid
      ariaLabel="HAS inputs"
      rows={rows.map((row) => ({
        abbr: row.abbr,
        label: row.label,
        value: row.value,
        tone: row.tone,
      }))}
    />
  );
}
