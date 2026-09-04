#!/usr/bin/env python3
"""Diff two affiliate-flags probe JSON dumps (FMLE one-flag A/B).

Usage:
  python desktop/scripts/diff-affiliate-flag-dumps.py before.json after.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    decoder = json.JSONDecoder()
    for index, ch in enumerate(raw):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(raw, index)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    raise SystemExit(f"No JSON object in {path}")


def decode_hex(hex_str: str) -> bytes:
    cleaned = "".join(ch for ch in hex_str if ch in "0123456789abcdefABCDEF")
    return bytes.fromhex(cleaned)


def diff_hex(before: str, after: str) -> list[dict]:
    a = decode_hex(before)
    b = decode_hex(after)
    n = min(len(a), len(b))
    changes = []
    for offset in range(n):
        if a[offset] != b[offset]:
            changes.append(
                {
                    "offset": offset,
                    "offsetHex": f"0x{offset:X}",
                    "before": a[offset],
                    "after": b[offset],
                    "beforeHex": f"0x{a[offset]:02X}",
                    "afterHex": f"0x{b[offset]:02X}",
                }
            )
    if len(a) != len(b):
        changes.append(
            {"note": "lengthMismatch", "beforeLen": len(a), "afterLen": len(b)}
        )
    return changes


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__.strip())
    before = load_json(Path(sys.argv[1]))
    after = load_json(Path(sys.argv[2]))
    before_slots = {
        slot.get("slot"): slot for slot in before.get("slots") or [] if isinstance(slot, dict)
    }
    after_slots = {
        slot.get("slot"): slot for slot in after.get("slots") or [] if isinstance(slot, dict)
    }
    report = {
        "beforeStatus": before.get("status"),
        "afterStatus": after.get("status"),
        "managedClubUid": after.get("managedClubUid") or before.get("managedClubUid"),
        "slotDiffs": [],
    }
    for slot_id in sorted(set(before_slots) | set(after_slots), key=lambda x: (x is None, x)):
        left = before_slots.get(slot_id) or {}
        right = after_slots.get(slot_id) or {}
        left_hex = left.get("structBytesHex") or ""
        right_hex = right.get("structBytesHex") or ""
        if not left_hex and not right_hex:
            continue
        changes = diff_hex(left_hex, right_hex) if left_hex and right_hex else []
        if left.get("linkStructPointer") != right.get("linkStructPointer"):
            changes.insert(
                0,
                {
                    "note": "linkStructPointerChanged",
                    "before": left.get("linkStructPointer"),
                    "after": right.get("linkStructPointer"),
                },
            )
        if not changes:
            continue
        report["slotDiffs"].append(
            {
                "slot": slot_id,
                "clubUid": right.get("clubUid") or left.get("clubUid"),
                "clubName": right.get("clubName") or left.get("clubName"),
                "feederCatalogMultiClub": right.get("feederCatalogMultiClub"),
                "changeCount": len([c for c in changes if "offset" in c]),
                "changes": changes,
            }
        )
    print(json.dumps(report, indent=2))
    if not report["slotDiffs"]:
        print("No byte changes across link-vector slots.", file=sys.stderr)


if __name__ == "__main__":
    main()
