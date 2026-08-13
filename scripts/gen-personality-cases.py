import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
flags = json.loads((root / "tmp-case-flags.json").read_text(encoding="utf-8"))
flags = [f for f in flags if f["id"] and f["id"] != "Personality"]

lines: list[str] = []
lines.append('import type { MediaCase } from "../catalog/types.js";')
lines.append("")
lines.append("export type PersonalityCaseFlags = {")
lines.append("  det: number[];")
lines.append("  other: number[];")
lines.append("  detNewgen: number[];")
lines.append("  otherNewgen: number[];")
lines.append("};")
lines.append("")
lines.append("/** Personality other-case OR rules from Evaluation. */")
lines.append("export const PERSONALITY_OTHER_CASES: MediaCase[] = [")

other_defs = [
    (1, "Pro 1-17 and/or Tem 1-9", [("professionalism", 1, 17), ("temperament", 1, 9)]),
    (2, "Amb 1-15 and/or Loy 10-20", [("ambition", 1, 15), ("loyalty", 10, 20)]),
    (3, "Amb 6-20 and/or Loy 1-10", [("ambition", 6, 20), ("loyalty", 1, 10)]),
    (4, "Loy 1-17 and/or Amb 8-20", [("loyalty", 1, 17), ("ambition", 8, 20)]),
    (5, "Tem 1-9 and/or Pre 1-14", [("temperament", 1, 9), ("pressure", 1, 14)]),
    (6, "Tem 10-20 and/or Amb 1-13", [("temperament", 10, 20), ("ambition", 1, 13)]),
]

for id_, label, branches in other_defs:
    lines.append("  {")
    lines.append(f"    id: {id_},")
    lines.append(f'    label: "{label}",')
    lines.append("    anyOf: [")
    for attr, lo, hi in branches:
        lines.append("      {")
        lines.append('        kind: "range",')
        lines.append(f'        attribute: "{attr}",')
        lines.append(f"        range: {{ min: {lo}, max: {hi} }},")
        lines.append("      },")
    lines.append("    ],")
    lines.append("  },")
lines.append("];")
lines.append("")
lines.append("/**")
lines.append(" * Cases (det) case 5 template: Spo 5-20.")
lines.append(" * Empirically the only det flag applied as a forward clamp in the sheet.")
lines.append(" */")
lines.append("export const DET_CASE_SPORTSMANSHIP = {")
lines.append("  id: 5,")
lines.append("  range: { min: 5, max: 20 },")
lines.append("} as const;")
lines.append("")
lines.append("/** Case flags from Personalities / Newgen Personalities sheets. */")
lines.append(
    "export const PERSONALITY_CASE_FLAGS: Record<string, PersonalityCaseFlags> = {"
)
for f in sorted(flags, key=lambda x: x["id"]):
    lines.append(f"  {json.dumps(f['id'])}: {{")
    lines.append(f"    det: {json.dumps(f['det'])},")
    lines.append(f"    other: {json.dumps(f['other'])},")
    lines.append(f"    detNewgen: {json.dumps(f['detNewgen'])},")
    lines.append(f"    otherNewgen: {json.dumps(f['otherNewgen'])},")
    lines.append("  },")
lines.append("};")
lines.append("")
lines.append("export function caseFlagsFor(")
lines.append("  personalityId: string,")
lines.append("  isRegen: boolean,")
lines.append("): { det: number[]; other: number[] } {")
lines.append("  const flags = PERSONALITY_CASE_FLAGS[personalityId];")
lines.append("  if (!flags) return { det: [], other: [] };")
lines.append("  const raw = isRegen")
lines.append("    ? { det: flags.detNewgen, other: flags.otherNewgen }")
lines.append("    : { det: flags.det, other: flags.other };")
lines.append("  return {")
lines.append("    det: [...new Set(raw.det)],")
lines.append("    other: [...new Set(raw.other)],")
lines.append("  };")
lines.append("}")
lines.append("")

out = root / "src" / "data" / "personality-cases.ts"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {out} ({len(flags)} personalities)")
