import { formatDelta } from "@/domain/attribute-history";
import { attributeDeltaTone } from "@/domain/attribute-tone";

export function AttrDeltaBadge({
  attribute,
  delta,
}: {
  attribute: string;
  delta: number | null | undefined;
}) {
  if (delta == null || delta === 0) return null;
  const tone = attributeDeltaTone(attribute, delta);
  if (!tone) return null;
  return (
    <span
      className={`attr-delta attr-tone attr-tone-${tone}`}
      aria-label={`Change ${formatDelta(delta)}`}
    >
      {formatDelta(delta)}
    </span>
  );
}
