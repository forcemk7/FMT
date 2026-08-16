"""T084: FT/II/U19 joins from this club's team object — synthetic blob, not a Career Save."""

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
II_TEAM = 1300
II_DUP = 4500
II_CLUB = 2200
JOBS_FT = [200 + i for i in range(8)]
JOBS_II = [300 + i for i in range(5)]
JOBS_YOUTH = [400 + i for i in range(6)]
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


def _list_blob(jobs: list[int]) -> bytes:
    return MOTIF + struct.pack("<H", len(jobs)) + b"".join(
        struct.pack("<I", j) for j in jobs
    )


def _affiliate_after(club_id: int, nested: str | None = None) -> bytes:
    layout = bytes([0x01]) + AFTER_MARKER + bytes(12) + struct.pack("<I", club_id)
    if nested:
        return _lp32(nested) + layout
    return layout


class UnitSquadsT084Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ft = _load("ft_t084", ROOT / "scripts" / "ft_squad_discovery.py")
        cls.ii = _load("ii_t084", ROOT / "scripts" / "ii_squad_discovery.py")
        cls.u19 = _load("u19_t084", ROOT / "scripts" / "u19_squad_discovery.py")

    def test_ft_joins_small_blob_outside_mb_window_and_count_gate(self) -> None:
        """Body at a few hundred bytes, 8 jobs — old 40–100MB / 15–45 gates miss."""
        catalog = _catalog_row(PARENT, TEAM_ID, DUP)
        pad = b"\x00" * 64
        body = _ft_body(TEAM_ID, DUP, PERSIST, JOBS_FT)
        blob = catalog + pad + body
        self.assertLess(len(blob), 1_000)
        hit = self.ft.resolve_ft_squad(blob, PARENT)
        self.assertIsNotNone(hit)
        assert hit is not None and hit.get("list")
        self.assertEqual(hit["team"]["teamId"], TEAM_ID)
        self.assertEqual(hit["list"]["jobs"], JOBS_FT)
        self.assertEqual(hit["list"]["count"], 8)
        selected = self.ft.select_managed_ft_jobs(PARENT, hit, fallback_jobs=DECOY_JOBS)
        self.assertEqual(selected["method"], "ft-club-squad-join-v1")
        self.assertEqual(selected["jobs"], JOBS_FT)

    def test_identity_known_join_miss_does_not_take_pick_tid(self) -> None:
        catalog = _catalog_row(PARENT, TEAM_ID, DUP)
        hit = self.ft.resolve_ft_squad(catalog, PARENT)
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertIsNone(hit.get("list"))
        selected = self.ft.select_managed_ft_jobs(
            PARENT, hit, fallback_jobs=DECOY_JOBS
        )
        self.assertEqual(selected["method"], "ft-club-squad-join-miss")
        self.assertEqual(selected["jobs"], [])
        self.assertEqual(selected["missReason"], "no-job-list")
        none_hit = self.ft.select_managed_ft_jobs(
            PARENT, None, fallback_jobs=DECOY_JOBS
        )
        self.assertEqual(none_hit["jobs"], [])
        self.assertEqual(none_hit["missReason"], "no-catalog")

    def test_ii_b_suffix_joins_without_ii_string(self) -> None:
        name = f"{PARENT} B"
        catalog = _catalog_row(name, II_TEAM, II_DUP, _affiliate_after(II_CLUB))
        blob = catalog + (b"\x00" * 48) + _subunit_body(II_TEAM, II_DUP, JOBS_II)
        self.assertNotIn(f"{PARENT} II".encode(), blob)
        hit = self.ii.resolve_ii_squad(blob, PARENT)
        self.assertIsNotNone(hit)
        assert hit is not None and hit.get("list")
        self.assertEqual(hit["iiName"], name)
        self.assertEqual(hit["list"]["jobs"], JOBS_II)

    def test_ii_nested_long_name_need_not_end_ii(self) -> None:
        name = f"{PARENT} U21"
        nested = f"{PARENT} Under-21"
        catalog = _catalog_row(
            name, II_TEAM, II_DUP, _affiliate_after(II_CLUB, nested=nested)
        )
        blob = catalog + (b"\x00" * 48) + _subunit_body(II_TEAM, II_DUP, JOBS_II)
        hit = self.ii.resolve_ii_squad(blob, PARENT)
        self.assertIsNotNone(hit)
        assert hit is not None and hit.get("list")
        self.assertEqual(hit["iiName"], name)
        self.assertEqual(hit["list"]["jobs"], JOBS_II)

    def test_missing_reserves_unit_is_absent_not_a_failed_join(self) -> None:
        catalog = _catalog_row(PARENT, TEAM_ID, DUP)
        blob = catalog + (b"\x00" * 48) + _ft_body(TEAM_ID, DUP, PERSIST, JOBS_FT)
        self.assertIsNone(self.ii.resolve_ii_squad(blob, PARENT))
        ft = self.ft.resolve_ft_squad(blob, PARENT)
        self.assertIsNotNone(ft)
        assert ft is not None
        self.assertEqual(ft["list"]["jobs"], JOBS_FT)

    def test_youth_u18_before_name_not_after_decoy(self) -> None:
        live = _list_blob(JOBS_YOUTH)
        decoy = _list_blob(DECOY_JOBS)
        name = f"{PARENT} U18".encode("utf-8")
        lp = struct.pack("<I", len(name)) + name
        pad_before = b"\x00" * 24
        blob = live + pad_before + lp + (b"\x00" * 12) + decoy
        hit = self.u19.resolve_u19_squad(blob, PARENT)
        self.assertIsNotNone(hit)
        assert hit is not None and hit.get("list")
        self.assertEqual(hit["u19Name"], f"{PARENT} U18")
        self.assertEqual(hit["list"]["jobs"], JOBS_YOUTH)
        self.assertLess(hit["list"]["delta"], 0)
        near = self.u19.parse_list_near_name(blob, blob.find(name), len(name))
        after = self.u19.parse_list_after_name(blob, blob.find(name), len(name))
        self.assertEqual(near["jobs"], JOBS_YOUTH)
        self.assertEqual(after["jobs"], DECOY_JOBS)

    def test_after_name_only_is_not_the_live_list(self) -> None:
        decoy = _list_blob(DECOY_JOBS)
        name = f"{PARENT} U19".encode("utf-8")
        lp = struct.pack("<I", len(name)) + name
        blob = lp + (b"\x00" * 8) + decoy
        name_abs = blob.find(name)
        self.assertIsNone(self.u19.parse_list_before_name(blob, name_abs))
        self.assertIsNotNone(self.u19.parse_list_after_name(blob, name_abs, len(name)))
        self.assertIsNone(self.u19.parse_list_near_name(blob, name_abs, len(name)))
        self.assertIsNone(self.u19.resolve_u19_squad(blob, PARENT))

    def test_no_body_lo_or_ft_count_constants_as_law(self) -> None:
        self.assertFalse(hasattr(self.ft, "BODY_LO"))
        self.assertFalse(hasattr(self.ft, "BODY_HI"))
        self.assertFalse(hasattr(self.ft, "FT_COUNT_LO"))
        self.assertFalse(hasattr(self.ft, "FT_COUNT_HI"))
        self.assertGreaterEqual(self.ii.SQUAD_COUNT_HI, 80)
        self.assertEqual(self.ii.JOB_LO, 100)


if __name__ == "__main__":
    unittest.main()
