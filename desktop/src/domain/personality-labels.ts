import type { LivePlayer } from "./adapters";
import { matchBestPersonalityCombo, type PersonalityComboLabels } from "../ha/match-best";
import type { MatchableAttrs } from "../ha/inference/match-combo";
import type { TrackedAttribute } from "../ha/domain/attributes";

/** Personality-pack keys required before we attempt a label (Ada excluded). */
const REQUIRED_PACK: Array<{ live: string; tracked: TrackedAttribute }> = [
  { live: "Ambition", tracked: "ambition" },
  { live: "Loyalty", tracked: "loyalty" },
  { live: "Pressure", tracked: "pressure" },
  { live: "Professionalism", tracked: "professionalism" },
  { live: "Sportsmanship", tracked: "sportsmanship" },
  { live: "Temperament", tracked: "temperament" },
  { live: "Controversy", tracked: "controversy" },
];

function readLiveAttr(value: number | null | undefined): number | null {
  return typeof value === "number" && value >= 1 && value <= 20 ? value : null;
}

/** Map live player attrs into combo-matcher input. */
export function liveMatchableAttrs(player: LivePlayer): MatchableAttrs | null {
  const pack = player.personalityAttributes ?? {};
  const attrs: MatchableAttrs = {};

  for (const { live, tracked } of REQUIRED_PACK) {
    const value = readLiveAttr(pack[live]);
    if (value == null) return null;
    attrs[tracked] = value;
  }

  const determination = readLiveAttr(player.attributes?.Determination);
  if (determination != null) attrs.determination = determination;

  const leadership = readLiveAttr(player.attributes?.Leadership);
  if (leadership != null) attrs.leadership = leadership;

  if (typeof player.age === "number" && Number.isFinite(player.age)) {
    attrs.age = player.age;
  }

  // Regen flag not on live player yet — treat as non-regen (regen-only labels skipped).
  attrs.isRegen = false;

  return attrs;
}

/** Inferred Personality + Media Handling for the Attributes General column. */
export function livePersonalityLabels(player: LivePlayer): PersonalityComboLabels | null {
  const attrs = liveMatchableAttrs(player);
  if (!attrs) return null;
  return matchBestPersonalityCombo(attrs);
}
