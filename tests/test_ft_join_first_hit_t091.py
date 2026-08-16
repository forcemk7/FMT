"""T091: FT join keeps scanning catalog hits until a 7f02 job-list exists."""

from __future__ import annotations

import importlib.util
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PRE_NAME = bytes.fromhex("0091000000ffffffff9100000091000000")
LIST_SENTINEL = bytes.fromhex("7f02000000ffffffff")
MOTIF = b"\xff\xff\xff\xff\x00\xff\xff\xff\xff"
AFTER_MARKER = bytes.fromhex("0000ffffffff00000100")

PARENT = "Sample Town"
TEAM_ID = 1200
DUP = 3400
PERSIST = 8800
DECOY_TEAM = 1199
DECOY_DUP = 3399
II_TEAM = 1300
II_DUP = 4500
II_DECOY_TEAM = 1299
II_DECOY_DUP = 4499
II_CLUB = 2200
JOBS_FT = [200 + i for i in range(8)]
JOBS_II = [300 + i for i in range(5)]
DECOY_JOBS = [9000 + i for i in range(12)]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _lp32(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack("<I", len(raw)) + raw


def _catalog_row(name: str, team_id: int, dup: int, after: bytes = b"") -> bytes:
    return struct.pack("<III", team_id, dup, dup) + PRE_NAME + _lp32(name) + after


def _ft_body(team_id: int, dup: int, persist: int, jobs: list[int]) -> bytes:
    body = (
        struct.pack("<I", team_id)
        + bytes(10)
        + struct.pack("<I", 0x1C00)
        + struct.pack("<II", dup, dup)
        + b"\x0a"
        + struct.pack("<I", persist)
        + LIST_SENTINEL
        + struct.pack("<H", len(jobs))
    )
    body += b"".join(struct.pack("<I", j) for j in jobs)
    return body


def _subunit_body(team_id: int, dup: int, jobs: list[int]) -> bytes:
    body = (
        struct.pack("<I", team_id)
        + bytes(10)
        + struct.pack("<I", 0x1C00)
        + struct.pack("<II", dup, dup)
        + b"\x0a"
        + MOTIF
        + struct.pack("<H", len(jobs))
    )
    body += b"".join(struct.pack("<I", j) for j in jobs)
    return body


def _affiliate_after(club_id: int) -> bytes:
    return bytes([0x01]) + AFTER_MARKER + bytes(12) + struct.pack("<I", club_id)


class FtJoinFirstHitT091Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ft = _load("ft_t091", ROOT / "scripts" / "ft_squad_discovery.py")
        cls.ii = _load("ii_t091", ROOT / "scripts" / "ii_squad_discovery.py")

    def test_second_catalog_object_wins_when_first_has_no_job_list(self) -> None:
        decoy = _catalog_row(PARENT, DECOY_TEAM, DECOY_DUP)
        live = _catalog_row(PARENT, TEAM_ID, DUP)
        body = _ft_body(TEAM_ID, DUP, PERSIST, JOBS_FT)
        blob = decoy + (b"\x00" * 32) + live + (b"\x00" * 64) + body
        hit = self.ft.resolve_ft_squad(blob, PARENT)
        self.assertIsNotNone(hit)
        assert hit is not None and hit.get("list")
        self.assertEqual(hit["team"]["teamId"], TEAM_ID)
        self.assertNotEqual(hit["team"]["teamId"], DECOY_TEAM)
        self.assertEqual(hit["list"]["jobs"], JOBS_FT)
        selected = self.ft.select_managed_ft_jobs(PARENT, hit, fallback_jobs=DECOY_JOBS)
        self.assertEqual(selected["method"], "ft-club-squad-join-v1")
        self.assertEqual(selected["jobs"], JOBS_FT)

    def test_identity_known_true_miss_never_pick_tid(self) -> None:
        decoy = _catalog_row(PARENT, DECOY_TEAM, DECOY_DUP)
        live = _catalog_row(PARENT, TEAM_ID, DUP)
        blob = decoy + (b"\x00" * 32) + live
        hit = self.ft.resolve_ft_squad(blob, PARENT)
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertIsNone(hit.get("list"))
        selected = self.ft.select_managed_ft_jobs(
            PARENT, hit, fallback_jobs=DECOY_JOBS
        )
        self.assertEqual(selected["method"], "ft-club-squad-join-miss")
        self.assertEqual(selected["jobs"], [])
        self.assertEqual(selected["missReason"], "no-job-list")
        self.assertNotEqual(selected["method"], "max_manager_staff_link_among_squad_lists")

    def test_body_hit_limit_expands_past_initial_bound(self) -> None:
        live = _catalog_row(PARENT, TEAM_ID, DUP)
        junk = (b"\xff" * 18) + struct.pack("<II", DUP, DUP)
        decoys = junk * (self.ii.BODY_HIT_LIMIT + 1)
        body = _ft_body(TEAM_ID, DUP, PERSIST, JOBS_FT)
        blob = live + decoys + body
        self.assertEqual(self.ii.BODY_HIT_LIMIT, 200)
        hit = self.ft.resolve_ft_squad(blob, PARENT)
        self.assertIsNotNone(hit)
        assert hit is not None and hit.get("list")
        self.assertEqual(hit["list"]["jobs"], JOBS_FT)

    def test_ii_second_catalog_wins_when_first_has_no_job_list(self) -> None:
        name = f"{PARENT} B"
        decoy = _catalog_row(
            name, II_DECOY_TEAM, II_DECOY_DUP, _affiliate_after(II_CLUB)
        )
        live = _catalog_row(name, II_TEAM, II_DUP, _affiliate_after(II_CLUB))
        blob = (
            decoy
            + (b"\x00" * 48)
            + live
            + (b"\x00" * 48)
            + _subunit_body(II_TEAM, II_DUP, JOBS_II)
        )
        hit = self.ii.resolve_ii_squad(blob, PARENT)
        self.assertIsNotNone(hit)
        assert hit is not None and hit.get("list")
        self.assertEqual(hit["team"]["teamId"], II_TEAM)
        self.assertNotEqual(hit["team"]["teamId"], II_DECOY_TEAM)
        self.assertEqual(hit["list"]["jobs"], JOBS_II)


if __name__ == "__main__":
    unittest.main()
