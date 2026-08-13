"""T007 regression: Abbe lookback 73 (per-unit); Millwood foreign attach in T012."""

from __future__ import annotations

import importlib.util
import json
import mmap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
EXTRACT = ROOT / "tmp" / "live-0112-extract.json"
PARENT = 920

ABBE_JOB, ABBE_UID, ABBE_CLUB = 366246, 2002266504, 904
RESVANIS_JOB, RESVANIS_CLUB = 364668, 911
DUNKEL_JOB, DUNKEL_CLUB = 352031, 911
ZETZMANN_JOB, ZETZMANN_CLUB = 236310, 904
KONYA_JOB = 221126  # II noise on Abbe motif — must stay untagged on II scan
MILLWOOD_JOB = 538884  # prior T004 hole class
CTRL_FT_JOBS = {106935, 334108, 285346, 364642, 113517}


def _load_extract() -> dict:
    raw = EXTRACT.read_bytes()
    for enc in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return json.loads(raw.decode(enc))
        except Exception:
            continue
    raise AssertionError("cannot decode live-0112-extract.json")


def _load_eft():
    spec = importlib.util.spec_from_file_location(
        "eft", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(BIN.is_file() and EXTRACT.is_file(), "live-0112 fixtures missing")
class TestLoanDetectT007(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.eft = _load_eft()
        data = _load_extract()
        cls.ft_jobs = {
            int(p["jobId"]) for p in data.get("players") or [] if p.get("jobId")
        }
        cls.ii_jobs = {
            int(p["jobId"])
            for p in (data.get("reserves") or {}).get("players") or []
            if p.get("jobId")
        }
        cls.u19_jobs = {
            int(p["jobId"])
            for p in (data.get("u19") or {}).get("players") or []
            if p.get("jobId")
        }
        # Ensure GT jobs present even if extract stale on gaps.
        cls.ft_jobs |= {ABBE_JOB, RESVANIS_JOB}
        cls.ii_jobs |= {DUNKEL_JOB, ZETZMANN_JOB, KONYA_JOB}
        cls.u19_jobs |= {MILLWOOD_JOB}
        with BIN.open("rb") as f:
            cls.mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        # Mirror extract: detect per unit.
        cls.ft_hit = cls.eft.detect_loaned_out_jobs(cls.mm, cls.ft_jobs, PARENT)
        cls.ii_hit = cls.eft.detect_loaned_out_jobs(cls.mm, cls.ii_jobs, PARENT)
        cls.u19_hit = cls.eft.detect_loaned_out_jobs(cls.mm, cls.u19_jobs, PARENT)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.mm.close()

    def test_lookback_hi_is_73(self) -> None:
        self.assertEqual(self.eft.LOAN_LOOKBACK_HI, 73)

    def test_abbe_and_resvanis_on_ft_unit(self) -> None:
        self.assertEqual(self.ft_hit.get(ABBE_JOB), ABBE_CLUB)
        self.assertEqual(self.ft_hit.get(RESVANIS_JOB), RESVANIS_CLUB)

    def test_zetzmann_dunkel_on_ii_unit_not_konya(self) -> None:
        self.assertEqual(self.ii_hit.get(ZETZMANN_JOB), ZETZMANN_CLUB)
        self.assertEqual(self.ii_hit.get(DUNKEL_JOB), DUNKEL_CLUB)
        self.assertNotIn(KONYA_JOB, self.ii_hit)

    def test_millwood_motif_still_untagged_foreign_is_t012(self) -> None:
        # Pad+motif still misses Millwood; foreign U19 list attach is T012.
        self.assertNotIn(MILLWOOD_JOB, self.u19_hit)

    def test_at_club_controls_miss_on_ft(self) -> None:
        for job in CTRL_FT_JOBS:
            self.assertNotIn(job, self.ft_hit, f"FP on at-club job {job}")

    def test_abbe_mentoring_exclude_contract(self) -> None:
        players = [
            {"uid": ABBE_UID, "jobId": ABBE_JOB, "name": "Lukas Abbe"},
            {"uid": 1, "jobId": 113517, "name": "Seimen"},
        ]
        self.eft.apply_loan_status(players, self.ft_hit, parent_club=PARENT)
        abbe = next(p for p in players if p["uid"] == ABBE_UID)
        seimen = next(p for p in players if p["uid"] == 1)
        self.assertEqual(abbe.get("loan", {}).get("status"), "loanedOut")
        self.assertIsNone(seimen.get("loan"))
        pool = [
            p
            for p in players
            if (p.get("loan") or {}).get("status") != "loanedOut"
        ]
        self.assertNotIn(ABBE_UID, {p["uid"] for p in pool})

    def test_suggest_cannot_seat_loaned_out_from_ft(self) -> None:
        players = [
            {"uid": job, "jobId": job, "name": f"job:{job}"} for job in self.ft_hit
        ]
        players.append({"uid": 1, "jobId": 113517, "name": "Seimen"})
        self.eft.apply_loan_status(players, self.ft_hit, parent_club=PARENT)
        pool = [
            p
            for p in players
            if (p.get("loan") or {}).get("status") != "loanedOut"
        ]
        self.assertEqual({p["uid"] for p in pool}, {1})


if __name__ == "__main__":
    unittest.main()
