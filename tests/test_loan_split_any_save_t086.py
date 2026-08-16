"""T086: at-club vs loaned-out is a loan object on unit jobs — synthetic only.

No Career Save names, UIDs, or loan counts. Same recipe FT / II / U19.
"""

from __future__ import annotations

import importlib.util
import io
import json
import mmap
import struct
import tempfile
import time
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = 2200
JOB_FT = 7_101
JOB_II = 7_201
JOB_U19 = 7_301
JOB_PACKED = [8_001 + i for i in range(8)]
HOST = 3344


def _load():
    spec = importlib.util.spec_from_file_location(
        "eft_t086", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
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
    tmp = tempfile.NamedTemporaryFile(prefix="fmt-t086-", suffix=".bin", delete=False)
    tmp.write(raw)
    tmp.flush()
    tmp.close()
    f = open(tmp.name, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    return mm, f, Path(tmp.name)


def _isolated_loan(job: int, club: int, *, eft, kind: int = 0x24) -> bytes:
    prefix = b"\x00" * 40
    at_job = prefix + struct.pack("<I", job)
    gap = b"\x00" * (41 - 4 - len(eft.LOAN_OUT_PAD))
    return at_job + gap + _loan_blob(kind, club, eft=eft)


class LoanSplitAnySaveT086Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.eft = _load()

    def test_loan_hits_for_unit_is_the_loan_object_recipe(self) -> None:
        src = self.eft.loan_hits_for_unit.__code__.co_names
        self.assertIn("detect_loaned_out_jobs", src)
        self.assertNotIn("detect_loaned_out_via_foreign_u19", src)

    def test_extract_main_does_not_call_foreign_u19(self) -> None:
        src = (ROOT / "scripts" / "extract-first-team-fast.py").read_text(
            encoding="utf-8"
        )
        main = src.split("def main", 1)[-1]
        self.assertNotIn("detect_loaned_out_via_foreign_u19", main)
        self.assertIn("loan_hits_for_unit", main)
        self.assertIn("emit_loan_census", main)

    def test_same_recipe_tags_ft_ii_u19(self) -> None:
        blob = (
            _isolated_loan(JOB_FT, HOST, eft=self.eft, kind=0x26)
            + _isolated_loan(JOB_II, HOST + 1, eft=self.eft, kind=0x24)
            + _isolated_loan(JOB_U19, HOST + 2, eft=self.eft, kind=0x24)
        )
        mm, fh, path = _mmap_bytes(blob)
        try:
            ft = self.eft.loan_hits_for_unit(mm, {JOB_FT}, PARENT)
            ii = self.eft.loan_hits_for_unit(mm, {JOB_II}, PARENT)
            u19 = self.eft.loan_hits_for_unit(mm, {JOB_U19}, PARENT)
            self.assertEqual(ft.get(JOB_FT), HOST)
            self.assertEqual(ii.get(JOB_II), HOST + 1)
            self.assertEqual(u19.get(JOB_U19), HOST + 2)
            self.assertNotIn(JOB_FT, ii)
            self.assertNotIn(JOB_FT, u19)
        finally:
            mm.close()
            fh.close()
            path.unlink(missing_ok=True)

    def test_packed_64ff24_stride_is_not_a_loan(self) -> None:
        last = JOB_PACKED[-1]
        packed = b"".join(struct.pack("<I", j) for j in JOB_PACKED)
        trailer = b"\x00" * 8
        blob = packed + trailer + _loan_blob(0x24, HOST, eft=self.eft)
        mm, fh, path = _mmap_bytes(blob)
        try:
            hit = self.eft.loan_hits_for_unit(mm, set(JOB_PACKED), PARENT)
            self.assertNotIn(last, hit)
            self.assertEqual(hit, {})
        finally:
            mm.close()
            fh.close()
            path.unlink(missing_ok=True)

    def test_squad_and_loans_are_exclusive(self) -> None:
        blob = _isolated_loan(JOB_FT, HOST, eft=self.eft)
        mm, fh, path = _mmap_bytes(blob)
        try:
            hit = self.eft.loan_hits_for_unit(mm, {JOB_FT, JOB_II}, PARENT)
            players = [
                {"jobId": JOB_FT, "name": "Alpha Out", "uid": 11},
                {"jobId": JOB_II, "name": "Beta Home", "uid": 12},
            ]
            self.eft.apply_loan_status(players, hit, parent_club=PARENT)
            squad = [
                p
                for p in players
                if (p.get("loan") or {}).get("status") != "loanedOut"
            ]
            loans = [
                p
                for p in players
                if (p.get("loan") or {}).get("status") == "loanedOut"
            ]
            self.assertEqual([p["name"] for p in squad], ["Beta Home"])
            self.assertEqual([p["name"] for p in loans], ["Alpha Out"])
            self.assertFalse({p["name"] for p in squad} & {p["name"] for p in loans})
            mentoring = squad
            self.assertNotIn("Alpha Out", [p["name"] for p in mentoring])
        finally:
            mm.close()
            fh.close()
            path.unlink(missing_ok=True)

    def test_job_without_loan_object_stays_at_club(self) -> None:
        mm, fh, path = _mmap_bytes(b"\x00" * 64 + struct.pack("<I", JOB_U19))
        try:
            hit = self.eft.loan_hits_for_unit(mm, {JOB_U19}, PARENT)
            self.assertEqual(hit, {})
            players = [{"jobId": JOB_U19, "name": "Youth Home", "uid": 13}]
            self.eft.apply_loan_status(players, hit, parent_club=PARENT)
            self.assertNotEqual(
                (players[0].get("loan") or {}).get("status"), "loanedOut"
            )
        finally:
            mm.close()
            fh.close()
            path.unlink(missing_ok=True)

    def test_census_omits_missing_unit_and_empty_loans_are_zero(self) -> None:
        ft = self.eft.census_unit_row("Town", [JOB_FT, JOB_II], {})
        youth = self.eft.census_unit_row("Town U19", [JOB_U19], {JOB_U19: HOST})
        census = self.eft.build_loan_census(
            club_id=PARENT,
            club_name="Sample Town",
            units=[ft, youth],
        )
        self.assertEqual(census["clubId"], PARENT)
        self.assertEqual(census["clubName"], "Sample Town")
        names = [u["name"] for u in census["units"]]
        self.assertEqual(names, ["Town", "Town U19"])
        self.assertNotIn("II", names)
        self.assertEqual(ft["employed"], 2)
        self.assertEqual(ft["atClub"], 2)
        self.assertEqual(ft["loaned"], 0)
        self.assertEqual(youth["employed"], 1)
        self.assertEqual(youth["atClub"], 0)
        self.assertEqual(youth["loaned"], 1)

        buf = io.StringIO()
        with redirect_stderr(buf):
            self.eft.emit_loan_census(time.perf_counter(), census)
        line = buf.getvalue().strip()
        self.assertTrue(line.startswith("PROGRESS "))
        payload = json.loads(line[len("PROGRESS ") :])
        self.assertEqual(payload["phase"], "census")
        self.assertEqual(payload["clubId"], PARENT)
        self.assertEqual(payload["clubName"], "Sample Town")
        self.assertEqual(payload["units"], census["units"])


if __name__ == "__main__":
    unittest.main()
