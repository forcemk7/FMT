"""T006 regression: managed club id → FT list join beats wrong pick_tid ranking."""

from __future__ import annotations

import importlib.util
import json
import mmap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
FIXTURE = ROOT / "data" / "fixtures" / "ft-club-squad-join-locked.json"


def _load_mod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(BIN.is_file() and FIXTURE.is_file(), "live-0112 / FT fixture missing")
class TestFtClubSquadJoinT006(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.lock = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.exp = cls.lock["expected"]["Schalke 04"]
        cls.ft = _load_mod("ft_squad_discovery", ROOT / "scripts" / "ft_squad_discovery.py")
        cls.eft = _load_mod(
            "eft_t006", ROOT / "scripts" / "extract-first-team-fast.py"
        )

    def test_resolve_ft_squad_matches_lock(self) -> None:
        with BIN.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                hit = self.ft.resolve_ft_squad(mm, "Schalke 04")
            finally:
                mm.close()
        self.assertIsNotNone(hit)
        assert hit is not None
        team = hit["team"]
        lst = hit["list"]
        self.assertIsNotNone(lst)
        assert lst is not None
        self.assertEqual(team["teamId"], self.exp["bodyTeamId"])
        self.assertEqual(team["dup"], self.exp["dup"])
        self.assertEqual(lst["persistTid"], self.exp["persistTid"])
        self.assertEqual(lst["jobsAbs"], self.exp["listAbs"])
        self.assertEqual(lst["count"], self.exp["listCount"])
        self.assertGreaterEqual(len(lst["jobs"]), 15)

    def test_wrong_manager_ranking_cannot_win_when_join_hits(self) -> None:
        """Poison pick_tid toward a foreign tid; join must still select Schalke FT."""
        with BIN.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                squads = self.eft.discover_squads(mm)
                hit = self.ft.resolve_ft_squad(mm, "Schalke 04")
            finally:
                mm.close()
        self.assertIn(self.exp["persistTid"], squads)
        # Foreign / decoy tid present on this save's ranked list historically.
        decoy = 15658
        self.assertIn(decoy, squads)
        poisoned = {tid: 0 for tid in squads}
        poisoned[decoy] = 99
        poisoned[self.exp["persistTid"]] = 0
        ranked = self.eft.pick_tid(squads, poisoned)
        self.assertEqual(ranked, decoy, "precondition: poisoned ranking prefers decoy")
        assert hit and hit.get("list")
        self.assertEqual(hit["list"]["persistTid"], self.exp["persistTid"])
        self.assertNotEqual(hit["list"]["persistTid"], decoy)

    def test_spot_check_fixture_players_on_joined_list(self) -> None:
        jobs_by_name = {
            name: int(job)
            for name, job in self.exp["spotCheckJobIds"].items()
        }
        with BIN.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                hit = self.ft.resolve_ft_squad(mm, "Schalke 04")
            finally:
                mm.close()
        assert hit and hit.get("list")
        job_set = set(hit["list"]["jobs"])
        found = [name for name, jid in jobs_by_name.items() if jid in job_set]
        self.assertGreaterEqual(
            len(found),
            5,
            f"expected ≥5 Schalke FT jobs on joined list, got {found}",
        )


if __name__ == "__main__":
    unittest.main()
