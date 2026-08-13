"""Ensure fixture RE players exist in history with uid/name/position."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

HIST = Path("data/history.json")
FIX = Path("data/fixtures/save-players.json")


def main() -> None:
    hist = json.loads(HIST.read_text(encoding="utf-8-sig"))
    fix = json.loads(FIX.read_text(encoding="utf-8-sig"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    save = next(
        (s for s in hist["saves"] if s["id"] == hist.get("activeSaveId")),
        hist["saves"][0],
    )
    if not save.get("name"):
        save["name"] = "FC Schalke 04 - Bastian König - FM24Career"

    by_uid = {
        str((p.get("labels") or {}).get("playerId")): p for p in save["players"]
    }
    added = []
    updated = []
    for fp in fix:
        uid = str(fp["uid"])
        if uid in by_uid and by_uid[uid] is not None:
            p = by_uid[uid]
            labs = p.setdefault("labels", {})
            labs["playerName"] = fp["name"]
            labs["playerId"] = uid
            labs["position"] = fp.get("pos") or labs.get("position")
            sig = p.setdefault("signals", {})
            sig.setdefault("determination", fp.get("det"))
            sig.setdefault("leadership", fp.get("lea"))
            sig.setdefault("age", fp.get("age"))
            sig["isRegen"] = fp.get("kind") == "NEWGEN"
            if not sig.get("personality"):
                sig["personality"] = ""
            if not sig.get("mediaHandling"):
                sig["mediaHandling"] = ""
            updated.append(fp["name"])
            continue
        entry = {
            "id": str(uuid.uuid4()),
            "createdAt": now,
            "updatedAt": now,
            "title": fp["name"],
            "signals": {
                "personality": "",
                "mediaHandling": "",
                "isRegen": fp.get("kind") == "NEWGEN",
                "determination": fp.get("det"),
                "leadership": fp.get("lea"),
                "age": fp.get("age"),
            },
            "labels": {
                "playerName": fp["name"],
                "playerId": uid,
                "position": fp.get("pos"),
            },
            "caseMode": "union_feasible",
            "snapshot": {},
        }
        save["players"].insert(0, entry)
        by_uid[uid] = entry
        added.append(fp["name"])

    save["updatedAt"] = now
    hist["panel"] = "players"
    hist["activeSaveId"] = save["id"]
    HIST.write_text(
        json.dumps(hist, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("save:", save["name"])
    print("added:", added or "(none)")
    print("updated:", updated or "(none)")


if __name__ == "__main__":
    main()
