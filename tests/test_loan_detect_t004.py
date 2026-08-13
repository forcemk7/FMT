"""T004 regression: loan detect ≠ Sipho-only; Vlad + II/U19 + gap UIDs."""

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

# Ground truth (T004A/B/C). Millwood hole closed in T012 via foreign U19 list.
# T007 Abbe/Resvanis/Dunkel need **per-unit** detect (see test_loan_detect_t007);
# combined FT+II pools still first-hit Zetzmann/Dunkel and miss Abbe/Resvanis.
EXPECT_LOAN = {
    382267: 1456,  # Sipho → Legia
    437615: 912,  # Vlad → Frankfurt
    506980: 916,  # Braescu → Köln
    506986: 2238,  # Manole → Augsburg
    365838: 2249,  # Öztürk
    315711: 946,  # Görrissen (gap FT)
    317202: 108997,  # Risse → Darmstadt (gap II; club>100k, back=57)
    351592: 2245,  # Pérez (gap II)
}
GAP_JOB_UID = {
    315711: 2002215969,  # Görrissen FT
    317202: 2002217460,  # Risse II
    351592: 2002251850,  # Pérez II
}
CTRL_FT_JOBS = {
    106935,  # Paco
    334108,  # Bandeira
    285346,  # Kizza
    364642,  # Jones
    113517,  # Seimen
}
MILLWOOD_JOB = 538884
VLAD_UID = 2002330407


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
class TestLoanDetectT004(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.eft = _load_eft()
        cls.data = _load_extract()
        jobs: set[int] = set()
        for p in cls.data.get("players") or []:
            if p.get("jobId"):
                jobs.add(int(p["jobId"]))
        for key in ("reserves", "u19"):
            block = cls.data.get(key) or {}
            for p in block.get("players") or []:
                if p.get("jobId"):
                    jobs.add(int(p["jobId"]))
        # Include gap jobs so detect can tag them once resolved into extract.
        jobs |= set(GAP_JOB_UID)
        jobs |= set(EXPECT_LOAN)
        cls.jobs = jobs
        with BIN.open("rb") as f:
            cls.mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        cls.hit = cls.eft.detect_loaned_out_jobs(cls.mm, cls.jobs, PARENT)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.mm.close()

    def test_not_sipho_only(self) -> None:
        self.assertGreater(len(self.hit), 1, "detect must tag more than Sipho")
        self.assertIn(382267, self.hit)
        self.assertIn(437615, self.hit, "Vlad must be tagged (was Sipho-only bug)")

    def test_gt_loan_clubs(self) -> None:
        for job, club in EXPECT_LOAN.items():
            self.assertEqual(
                self.hit.get(job),
                club,
                f"job {job} expected loan club {club}",
            )

    def test_at_club_controls_miss(self) -> None:
        for job in CTRL_FT_JOBS:
            self.assertNotIn(job, self.hit, f"FP on at-club job {job}")

    def test_millwood_foreign_u19_not_in_combined_motif_pool(self) -> None:
        # Motif-only combined pool still misses Millwood; T012 foreign attach is
        # separate (see test_loan_detect_t012).
        self.assertNotIn(MILLWOOD_JOB, self.hit)

    def test_gap_double_uid_fallback(self) -> None:
        resolved = self.eft.resolve_job_uids_double_fallback(
            self.mm, list(GAP_JOB_UID)
        )
        self.assertEqual(resolved, GAP_JOB_UID)

    def test_gap_jobs_loan_tagged_when_in_pool(self) -> None:
        """Gap jobs must be loan-tagged once present in the squad job set."""
        for job, club in (
            (315711, 946),
            (317202, 108997),
            (351592, 2245),
        ):
            self.assertEqual(
                self.hit.get(job),
                club,
                f"gap job {job} expected loan club {club}",
            )

    def test_vlad_mentoring_exclude_contract(self) -> None:
        """Mentoring pool excludes loanedOut — Vlad must carry that status."""
        players = [
            {"uid": VLAD_UID, "jobId": 437615, "name": "Moise Vlad-Paul"},
            {"uid": 1, "jobId": 113517, "name": "Seimen"},
        ]
        self.eft.apply_loan_status(players, self.hit, parent_club=PARENT)
        vlad = next(p for p in players if p["uid"] == VLAD_UID)
        seimen = next(p for p in players if p["uid"] == 1)
        self.assertEqual(vlad.get("loan", {}).get("status"), "loanedOut")
        self.assertIsNone(seimen.get("loan"))
        # Mirror web firstTeamMentoringPlayers filter.
        pool = [
            p
            for p in players
            if (p.get("loan") or {}).get("status") != "loanedOut"
        ]
        self.assertNotIn(VLAD_UID, {p["uid"] for p in pool})
        self.assertIn(1, {p["uid"] for p in pool})


if __name__ == "__main__":
    unittest.main()
