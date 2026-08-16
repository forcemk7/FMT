"""T085: HA/CA for listed people — UniqueID band is a heuristic, not a drop filter.

Synthetic blob only. No Career Save UniqueIDs, names, or floors.
"""

from __future__ import annotations

import importlib.util
import struct
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

JOB = 7_001
JOB_GAP = 7_003
UID_OOB = 42_424_242
UID_BAND = 1_800_000_001
UID_NEWGEN = 2_100_000_001
FIRST = "Pat"
LAST = "Sample"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _lp32(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack("<I", len(raw)) + raw


def _employment(job: int, uid: int, tag: int = 0x09) -> bytes:
    return bytes([tag, 0x02]) + struct.pack("<I", job) + b"\x02" + struct.pack("<I", uid)


def _double(uid: int) -> bytes:
    return struct.pack("<II", uid, uid)


def _name_near(uid: int) -> bytes:
    return b"\x00\x02" + struct.pack("<I", uid) + _lp32(FIRST) + _lp32(LAST)


def _pack() -> bytes:
    lead = b"\x00" * 6
    attrs = bytes([8, 9, 10, 11, 12, 13, 14, 7])
    return lead + attrs + b"\x00\x00" + bytes([0, 0, 0, 0, 0, 0, 1])


def _attr_card() -> bytes:
    rec = bytearray(69)
    for i in range(22):
        rec[i] = 50
    rec[23] = 12
    rec[34] = 0
    rec[35] = 0
    rec[36] = 1
    rec[37] = 0
    rec[43] = 1
    for i in range(55, 69):
        rec[i] = 50
    return bytes(rec)


def _person_with_pack_and_card(uid: int) -> bytes:
    card = _attr_card()
    pack = _pack()
    name = _name_near(uid)
    dab_pad = 2_000 - len(card) - len(pack) - len(name)
    assert dab_pad > 0
    return card + (b"\x00" * dab_pad) + pack + name + _double(uid)


class HaCaAnySaveT085Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.eft = _load("eft_t085", ROOT / "scripts" / "extract-first-team-fast.py")

    def test_band_is_heuristic_not_law(self) -> None:
        self.assertTrue(self.eft.uid_in_continue_career_band(UID_BAND))
        self.assertFalse(self.eft.uid_in_continue_career_band(UID_OOB))
        self.assertTrue(self.eft.plausible_person_uid(UID_OOB, JOB))
        self.assertFalse(self.eft.plausible_person_uid(1, JOB))
        self.assertFalse(self.eft.plausible_person_uid(JOB, JOB))

    def test_oob_employment_with_person_double_is_kept(self) -> None:
        blob = _double(UID_OOB) + (b"\x00" * 16) + _employment(JOB, UID_OOB)
        mapped = self.eft.resolve_job_uids_batch(blob, [JOB])
        self.assertEqual(mapped.get(JOB), UID_OOB)

    def test_oob_without_double_does_not_steal_garbage_uid(self) -> None:
        blob = _employment(JOB, UID_OOB)
        mapped = self.eft.resolve_job_uids_batch(blob, [JOB])
        self.assertNotIn(JOB, mapped)

    def test_in_band_employment_still_maps_without_double(self) -> None:
        blob = _employment(JOB, UID_BAND)
        mapped = self.eft.resolve_job_uids_batch(blob, [JOB])
        self.assertEqual(mapped.get(JOB), UID_BAND)

    def test_in_band_preferred_when_both_employment_hits_exist(self) -> None:
        blob = (
            _double(UID_OOB)
            + _employment(JOB, UID_OOB)
            + _employment(JOB, UID_BAND)
        )
        mapped = self.eft.resolve_job_uids_batch(blob, [JOB])
        self.assertEqual(mapped.get(JOB), UID_BAND)

    def test_gap_double_fallback_keeps_oob_uid_uid(self) -> None:
        blob = struct.pack("<I", JOB_GAP) + _double(UID_OOB)
        mapped = self.eft.resolve_job_uids_double_fallback(blob, [JOB_GAP])
        self.assertEqual(mapped.get(JOB_GAP), UID_OOB)

    def test_listed_player_kept_when_uid_unresolved(self) -> None:
        jobs = [JOB]
        players = self.eft.build_players_from_jobs(
            b"\x00" * 32,
            jobs,
            {},
            names_only=True,
            t0=time.perf_counter(),
            phase="players",
        )
        self.assertEqual(len(players), 1)
        self.assertEqual(players[0]["jobId"], JOB)
        self.assertEqual(players[0]["uid"], 0)
        self.assertIsNone(players[0]["attributes"])

    def test_oob_pack_and_ca_card_once_each(self) -> None:
        body = _person_with_pack_and_card(UID_OOB)
        blob = body + (b"\x00" * 32) + _employment(JOB, UID_OOB)
        mapped = self.eft.resolve_job_uids_batch(blob, [JOB])
        self.assertEqual(mapped.get(JOB), UID_OOB)
        players = self.eft.build_players_from_jobs(
            blob,
            [JOB],
            mapped,
            names_only=False,
            t0=time.perf_counter(),
            phase="players",
        )
        self.assertEqual(len(players), 1)
        p = players[0]
        self.assertEqual(p["uid"], UID_OOB)
        self.assertEqual(p["kind"], "UNKNOWN")
        general = (p.get("attributes") or {}).get("general") or {}
        self.assertEqual(general.get("ambition"), 9)
        mental = (p.get("attributes") or {}).get("mental") or {}
        self.assertIsNotNone(mental.get("determination"))
        ext = p.get("_extract") or {}
        self.assertIsNotNone(ext.get("personalityPackAbs"))
        self.assertIsNotNone(ext.get("attrCardAbs"))
        self.assertNotEqual(ext.get("personalityPackAbs"), ext.get("attrCardAbs"))

    def test_oob_blobs_miss_stay_dash(self) -> None:
        blob = _double(UID_OOB) + (b"\x00" * 16) + _employment(JOB, UID_OOB)
        mapped = self.eft.resolve_job_uids_batch(blob, [JOB])
        players = self.eft.build_players_from_jobs(
            blob,
            [JOB],
            mapped,
            names_only=False,
            t0=time.perf_counter(),
            phase="players",
        )
        self.assertEqual(len(players), 1)
        self.assertEqual(players[0]["uid"], UID_OOB)
        self.assertIsNone(players[0]["attributes"])
        ext = players[0].get("_extract") or {}
        self.assertIsNone(ext.get("personalityPackAbs"))
        self.assertIsNone(ext.get("attrCardAbs"))

    def test_newgen_floor_only_inside_continue_career_band(self) -> None:
        self.assertEqual(self.eft.person_population_kind(UID_BAND), "REAL")
        self.assertEqual(self.eft.person_population_kind(UID_NEWGEN), "NEWGEN")
        self.assertEqual(self.eft.person_population_kind(UID_OOB), "UNKNOWN")
        self.assertEqual(self.eft.person_population_kind(0), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
