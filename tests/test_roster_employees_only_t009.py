"""T009: roster / Mentoring pool = managed-club employees only."""

from __future__ import annotations

import importlib.util
import json
import mmap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
FT_FIXTURE = ROOT / "data" / "fixtures" / "ft-club-squad-join-locked.json"
U19_FIXTURE = ROOT / "data" / "fixtures" / "u19-squad-namelist-locked.json"

# Foreign persist-tid historically preferred by poisoned pick_tid (T006).
DECOY_TID = 15658
PARENT = 920


def _load_mod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(BIN.is_file() and FT_FIXTURE.is_file(), "live-0112 / FT fixture missing")
class TestRosterEmployeesOnlyT009(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.lock = json.loads(FT_FIXTURE.read_text(encoding="utf-8"))
        cls.exp = cls.lock["expected"]["Schalke 04"]
        cls.ft = _load_mod("ft_t009", ROOT / "scripts" / "ft_squad_discovery.py")
        cls.eft = _load_mod("eft_t009", ROOT / "scripts" / "extract-first-team-fast.py")
        cls.u19 = _load_mod("u19_t009", ROOT / "scripts" / "u19_squad_discovery.py")
        cls.ii = _load_mod("ii_t009", ROOT / "scripts" / "ii_squad_discovery.py")

    def test_select_refuses_fallback_when_club_identity_known(self) -> None:
        """Non-employee decoy jobs must not win FT membership via pick_tid."""
        decoy_jobs = [184940, 186575, 189933]
        selected = self.ft.select_managed_ft_jobs(
            "Schalke 04",
            None,
            fallback_jobs=decoy_jobs,
        )
        self.assertEqual(selected["method"], "ft-club-squad-join-miss")
        self.assertEqual(selected["jobs"], [])
        for jid in decoy_jobs:
            self.assertNotIn(jid, selected["jobs"])

    def test_join_wins_and_excludes_decoy_jobs(self) -> None:
        with BIN.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                hit = self.ft.resolve_ft_squad(mm, "Schalke 04")
                squads = self.eft.discover_squads(mm)
            finally:
                mm.close()
        self.assertIsNotNone(hit)
        assert hit is not None and hit.get("list")
        selected = self.ft.select_managed_ft_jobs("Schalke 04", hit, fallback_jobs=[1, 2, 3])
        self.assertEqual(selected["method"], "ft-club-squad-join-v1")
        join_jobs = set(selected["jobs"])
        self.assertEqual(selected["persistTid"], self.exp["persistTid"])
        self.assertGreaterEqual(len(join_jobs), 15)

        self.assertIn(DECOY_TID, squads)
        decoy_jobs = set(squads[DECOY_TID][2])
        self.assertTrue(decoy_jobs)
        self.assertFalse(
            join_jobs & decoy_jobs,
            "foreign decoy list must not share jobs with managed FT employees",
        )

    def test_mentoring_pool_subset_of_join_employees(self) -> None:
        """Mentoring Suggest candidates ⊆ FT employees ∩ ¬loanedOut."""
        with BIN.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                hit = self.ft.resolve_ft_squad(mm, "Schalke 04")
                assert hit and hit.get("list")
                jobs = list(hit["list"]["jobs"])
                loaned = self.eft.detect_loaned_out_jobs(mm, set(jobs), PARENT)
            finally:
                mm.close()
        selected = self.ft.select_managed_ft_jobs("Schalke 04", hit)
        employee_jobs = set(selected["jobs"])
        mentoring_jobs = employee_jobs - set(loaned)
        # Decoy foreign jobs cannot enter Mentoring pool.
        decoy_sample = {184940, 186575, 189933, 225741, 250232}
        self.assertFalse(decoy_sample & mentoring_jobs)
        self.assertFalse(decoy_sample & employee_jobs)
        # Loaned-out employees stay classifiable but never seat.
        for jid in loaned:
            self.assertIn(jid, employee_jobs)
            self.assertNotIn(jid, mentoring_jobs)

    def test_spot_check_no_u19_decoy_names(self) -> None:
        if not U19_FIXTURE.is_file():
            self.skipTest("U19 fixture missing")
        u19_lock = json.loads(U19_FIXTURE.read_text(encoding="utf-8"))
        exp = u19_lock["expected"]["Schalke 04"]
        with BIN.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                hit = self.u19.resolve_u19_squad(mm, "Schalke 04")
            finally:
                mm.close()
        self.assertIsNotNone(hit)
        assert hit is not None
        lst = hit.get("list") or {}
        # Before-name employee list (negative delta); after-name decoys are junk.
        self.assertLess(int(lst.get("delta") or 0), 0)
        self.assertEqual(lst.get("count"), exp["listCount"])


if __name__ == "__main__":
    unittest.main()
