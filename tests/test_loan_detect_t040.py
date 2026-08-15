"""T040: at-club II must not be tagged via list-adjacent team-body 64ff24."""

from __future__ import annotations

import importlib.util
import mmap
import struct
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KOENIG_BIN = ROOT / "tmp" / "t040-koenig.bin"
PARENT = 920
PARENT_SHORT = "Schalke 04"
ITU_JOB = 516374
ITU_UID = 2002400248
MILLWOOD_JOB = 538884
DAVSYKIBA_JOB = 538997
KASPRAKOV_JOB = 538940
BOXLEITNER_JOB = 439456
MANOLE_JOB = 506986
ZETZMANN_JOB = 236310
DUNKEL_JOB = 352031


def _load_eft():
    spec = importlib.util.spec_from_file_location(
        "eft_t040", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _loan_blob(kind: int, club: int, *, eft) -> bytes:
    pad = eft.LOAN_OUT_PAD
    motif = bytes((0x64, 0xFF, kind))
    a = struct.pack("<I", 0x1B)
    zeros10 = b"\x00" * 10
    b = struct.pack("<I", 0x1C18)
    clubs = struct.pack("<I", club) * 2
    marker = struct.pack("<H", 0x000A)
    return pad + motif + a + zeros10 + b + clubs + marker


def _mmap_bytes(raw: bytes):
    tmp = tempfile.NamedTemporaryFile(prefix="fmt-t040-", suffix=".bin", delete=False)
    tmp.write(raw)
    tmp.flush()
    tmp.close()
    f = open(tmp.name, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    return mm, f, Path(tmp.name)


class TestLoanDetectT040Synthetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.eft = _load_eft()

    def test_stride_threshold_is_3(self) -> None:
        self.assertEqual(self.eft.LOAN_LIST_STRIDE4_RUN_MIN, 3)

    def test_packed_ii_list_does_not_tag_last_job(self) -> None:
        jobs = [400001 + i for i in range(8)]
        last = jobs[-1]
        packed = b"".join(struct.pack("<I", j) for j in jobs)
        # Last job starts 25 bytes before motif (König II / Itu geometry).
        trailer = b"\x00" * 8
        blob = packed + trailer + _loan_blob(0x24, 3609393, eft=self.eft)
        mm, fh, path = _mmap_bytes(blob)
        try:
            motif_at = blob.index(b"\x64\xff")
            self.assertEqual(motif_at - (len(packed) - 4), 25)
            hit = self.eft.detect_loaned_out_jobs(mm, set(jobs), PARENT)
            self.assertNotIn(last, hit)
            self.assertEqual(hit, {})
        finally:
            mm.close()
            fh.close()
            path.unlink(missing_ok=True)

    def test_isolated_true_loan_still_tags(self) -> None:
        job = 506986
        prefix = b"\x00" * 40
        at_job = prefix + struct.pack("<I", job)
        # back=41: job start → motif, including the 13-byte pad in _loan_blob.
        gap = b"\x00" * (41 - 4 - len(self.eft.LOAN_OUT_PAD))
        blob = at_job + gap + _loan_blob(0x24, 2238, eft=self.eft)
        mm, fh, path = _mmap_bytes(blob)
        try:
            motif_at = blob.index(b"\x64\xff")
            self.assertEqual(motif_at - len(prefix), 41)
            hit = self.eft.detect_loaned_out_jobs(mm, {job}, PARENT)
            self.assertEqual(hit.get(job), 2238)
        finally:
            mm.close()
            fh.close()
            path.unlink(missing_ok=True)

    def test_two_adjacent_jobs_still_tag_closest(self) -> None:
        # Konya-class noise is a 2-run; must not use the list reject.
        a, b = 221126, 221130
        packed = struct.pack("<I", a) + struct.pack("<I", b)
        trailer = b"\x00" * 8
        blob = packed + trailer + _loan_blob(0x26, 1456, eft=self.eft)
        mm, fh, path = _mmap_bytes(blob)
        try:
            hit = self.eft.detect_loaned_out_jobs(mm, {a, b}, PARENT)
            self.assertEqual(hit.get(b), 1456)
            self.assertNotIn(a, hit)
        finally:
            mm.close()
            fh.close()
            path.unlink(missing_ok=True)


@unittest.skipUnless(KOENIG_BIN.is_file(), "tmp/t040-koenig.bin missing")
class TestLoanDetectT040Koenig(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.eft = _load_eft()
        from ii_squad_discovery import resolve_ii_squad
        from u19_squad_discovery import resolve_u19_squad

        cls._fh = KOENIG_BIN.open("rb")
        cls.mm = mmap.mmap(cls._fh.fileno(), 0, access=mmap.ACCESS_READ)
        cls.ii_jobs = set(resolve_ii_squad(cls.mm, PARENT_SHORT)["list"]["jobs"])
        cls.u19_jobs = set(resolve_u19_squad(cls.mm, PARENT_SHORT)["list"]["jobs"])
        cls.ii_loan = cls.eft.detect_loaned_out_jobs(cls.mm, cls.ii_jobs, PARENT)
        cls.u19_loan = cls.eft.merge_loan_hits(
            cls.eft.detect_loaned_out_jobs(cls.mm, cls.u19_jobs, PARENT),
            cls.eft.detect_loaned_out_via_foreign_u19(
                cls.mm, cls.u19_jobs, PARENT, PARENT_SHORT
            ),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.mm.close()
        cls._fh.close()

    def test_itu_on_ii_not_loaned_out(self) -> None:
        self.assertIn(ITU_JOB, self.ii_jobs)
        self.assertNotIn(ITU_JOB, self.u19_jobs)
        self.assertNotIn(ITU_JOB, self.ii_loan)
        self.assertNotIn(ITU_JOB, self.u19_loan)

    def test_itu_not_rehomed_to_u19(self) -> None:
        reserves = {
            "players": [
                {
                    "jobId": ITU_JOB,
                    "uid": ITU_UID,
                    "name": "Adrian Itu",
                    "kind": "NEWGEN",
                }
            ]
        }
        self.eft.apply_loan_status(
            reserves["players"], self.ii_loan, parent_club=PARENT
        )
        u19 = {"players": []}
        self.eft.rehome_loaned_newgen_to_u19(reserves, u19)
        self.assertEqual(reserves["players"][0]["uid"], ITU_UID)
        self.assertNotEqual(
            (reserves["players"][0].get("loan") or {}).get("status"),
            "loanedOut",
        )
        self.assertEqual(u19["players"], [])

    def test_t012_outgoing_still_tagged(self) -> None:
        self.assertEqual(self.u19_loan.get(MILLWOOD_JOB), 2589)
        self.assertIn(DAVSYKIBA_JOB, self.u19_loan)
        self.assertEqual(self.u19_loan.get(KASPRAKOV_JOB), 877204)
        self.assertNotIn(MILLWOOD_JOB, self.ii_jobs)
        self.assertNotIn(DAVSYKIBA_JOB, self.ii_jobs)
        self.assertNotIn(KASPRAKOV_JOB, self.ii_jobs)

    def test_domestic_ii_loans_still_tagged(self) -> None:
        self.assertEqual(self.ii_loan.get(MANOLE_JOB), 2238)
        self.assertEqual(self.ii_loan.get(ZETZMANN_JOB), 904)
        self.assertEqual(self.ii_loan.get(DUNKEL_JOB), 911)

    def test_boxleitner_not_on_ii_this_save(self) -> None:
        # Returned to U19 namelist; no longer the II last-job / rehome path.
        self.assertNotIn(BOXLEITNER_JOB, self.ii_jobs)
        self.assertIn(BOXLEITNER_JOB, self.u19_jobs)


if __name__ == "__main__":
    unittest.main()
