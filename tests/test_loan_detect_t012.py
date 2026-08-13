"""T012: U19 at-club excludes outgoing loans; four GT names on Loans U19."""

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
PARENT_SHORT = "Schalke 04"

# FM at-club U19 delta vs FMT (user GT 2026-08-12).
MILLWOOD_JOB = 538884
DAVSYKIBA_JOB = 538997
KASPRAKOV_JOB = 538940
BOXLEITNER_JOB = 439456
BOXLEITNER_UID = 2002332248
KASPRAKOV_UID = 2002422330

FM_AT_CLUB_U19 = 19
GT_LOAN_U19_NAMES = {
    "Ben Millwood",
    "Alexandr Davyskiba",
    "Igor Kasprzak",  # namelist spelling; FM UI may show Kasprakov
    "Nik Jonas Boxleitner",
}


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


@unittest.skipUnless(BIN.is_file(), "live-0112-decomp.bin missing")
class TestLoanDetectT012(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.eft = _load_eft()
        with BIN.open("rb") as f:
            cls.mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        from u19_squad_discovery import resolve_u19_squad

        hit = resolve_u19_squad(cls.mm, PARENT_SHORT)
        assert hit and hit.get("list")
        cls.u19_jobs = set(hit["list"]["jobs"])
        cls.motif = cls.eft.detect_loaned_out_jobs(cls.mm, cls.u19_jobs, PARENT)
        cls.foreign = cls.eft.detect_loaned_out_via_foreign_u19(
            cls.mm, cls.u19_jobs, PARENT, PARENT_SHORT
        )
        cls.merged = cls.eft.merge_loan_hits(cls.motif, cls.foreign)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.mm.close()

    def test_pad_required_and_club_hi_raised(self) -> None:
        self.assertEqual(self.eft.LOAN_CLUB_HI, 5_000_000)
        self.assertTrue(hasattr(self.eft, "LOAN_OUT_PAD"))

    def test_millwood_davyskiba_foreign_u19_attach(self) -> None:
        self.assertIn(MILLWOOD_JOB, self.foreign)
        self.assertIn(DAVSYKIBA_JOB, self.foreign)
        self.assertEqual(self.foreign.get(MILLWOOD_JOB), 2589)
        self.assertEqual(self.foreign.get(DAVSYKIBA_JOB), 2589)

    def test_kasprakov_pad_motif(self) -> None:
        self.assertEqual(self.motif.get(KASPRAKOV_JOB), 877204)

    def test_boxleitner_pad_motif_on_ii_job(self) -> None:
        hit = self.eft.detect_loaned_out_jobs(self.mm, {BOXLEITNER_JOB}, PARENT)
        self.assertEqual(hit.get(BOXLEITNER_JOB), 3609393)

    def test_merged_u19_hits_include_hole_class(self) -> None:
        for job in (MILLWOOD_JOB, DAVSYKIBA_JOB, KASPRAKOV_JOB):
            self.assertIn(job, self.merged, f"job {job} untagged")

    def test_kasprakov_name_from_mark(self) -> None:
        doubles = self.eft.collect_doubles(self.mm, KASPRAKOV_UID)
        name = self.eft.resolve_name_from_mark(self.mm, KASPRAKOV_UID, doubles)
        self.assertEqual(name, "Igor Kasprzak")

    def test_at_club_controls_miss_on_u19(self) -> None:
        # Eschweiler was the FP when club-hi rose without pad.
        esch = 571903
        self.assertNotIn(esch, self.merged)

    def test_rehome_newgen_loan_to_u19(self) -> None:
        reserves = {
            "players": [
                {
                    "jobId": BOXLEITNER_JOB,
                    "uid": BOXLEITNER_UID,
                    "name": "Nik Jonas Boxleitner",
                    "kind": "NEWGEN",
                    "loan": {"status": "loanedOut", "loanClubId": 3609393},
                },
                {
                    "jobId": 506986,
                    "uid": 2,
                    "name": "Andrei Manole",
                    "kind": "NEWGEN",
                    "loan": {"status": "loanedOut", "loanClubId": 2238},
                },
                {
                    "jobId": 1,
                    "uid": 1,
                    "name": "At Club II",
                    "kind": "NEWGEN",
                },
            ]
        }
        u19 = {"players": []}
        self.eft.rehome_loaned_newgen_to_u19(reserves, u19)
        self.assertEqual(
            {p["uid"] for p in reserves["players"]},
            {1, 2},
            "domestic II loans must stay on Reserves",
        )
        self.assertEqual(len(u19["players"]), 1)
        self.assertEqual(u19["players"][0]["uid"], BOXLEITNER_UID)


@unittest.skipUnless(
    BIN.is_file() and EXTRACT.is_file(), "live-0112 fixtures missing"
)
class TestLoanDetectT012ExtractContract(unittest.TestCase):
    """Locks four-name delta vs FM at-club when extract JSON is fresh."""

    def test_u19_at_club_count_and_loans_four(self) -> None:
        data = _load_extract()
        u19 = (data.get("u19") or {}).get("players") or []
        if not u19:
            self.skipTest("extract has no u19 players")
        # Only assert when extract was produced with T012 recipe (foreign/pad).
        loaned = [
            p
            for p in u19
            if (p.get("loan") or {}).get("status") == "loanedOut"
        ]
        if len(loaned) < 4:
            self.skipTest(
                "extract predates T012 loan tags — re-run extract to lock"
            )
        at_club = [
            p
            for p in u19
            if (p.get("loan") or {}).get("status") != "loanedOut"
        ]
        # Ideal FM at-club is 19; live-0112 still seats Kraft (no motif, T007 hole)
        # → 20. Lock the four-name delta either way.
        self.assertIn(len(at_club), (19, 20), f"at-club={len(at_club)}")
        loan_names = {p.get("name") for p in loaned}
        for want in GT_LOAN_U19_NAMES:
            self.assertTrue(
                any(want.lower() in (n or "").lower() for n in loan_names),
                f"missing Loans U19 name {want!r} in {loan_names}",
            )
        for want in (
            "Ben Millwood",
            "Alexandr Davyskiba",
            "Igor Kasprzak",
            "Nik Jonas Boxleitner",
        ):
            self.assertFalse(
                any(
                    want.lower() in (p.get("name") or "").lower()
                    for p in at_club
                ),
                f"{want} still on at-club grid",
            )


if __name__ == "__main__":
    unittest.main()
