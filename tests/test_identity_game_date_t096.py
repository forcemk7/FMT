"""T096: identity neighborhood date — never the 24MB calendar-table day."""

from __future__ import annotations

import importlib.util
import struct
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TAG_01 = bytes.fromhex("00950e01")
TAG_02 = bytes.fromhex("00950e02")
PERSON = "Pat Example"
CLUB = "Sample Town"
CLUB_UID = 4242
TWIN = 0x11111111
TODAY = date(2026, 8, 16)
TABLE_END = date(2038, 5, 25)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _lp32(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack("<I", len(raw)) + raw


def _identity_blob(tag: bytes, person: str, club: str, uid: int) -> bytes:
    return tag + _lp32(person) + _lp32(club) + struct.pack("<I", uid)


def _days(d: date) -> int:
    return (d - date(1900, 1, 1)).days


def _prelude(mod, d: date) -> bytes:
    return mod.GAME_DATE_PRELUDE + struct.pack("<III", _days(d), TWIN, TWIN)


def _today_ptr(d: date) -> bytes:
    n = _days(d)
    return struct.pack("<II", n - 1, n) + b"\x00\x00\x00\x00"


def _table(mod, end: date, n: int = 10) -> bytes:
    start = end - timedelta(days=n - 1)
    return b"".join(_prelude(mod, start + timedelta(days=i)) for i in range(n))


class IdentityGameDateT096Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.emt = _load("emt_t096", ROOT / "scripts" / "extract-managed-team.py")
        cls.eft = _load("eft_t096", ROOT / "scripts" / "extract-first-team-fast.py")

    def test_t083_tags_still_parse(self) -> None:
        for tag in (TAG_01, TAG_02):
            blob = _identity_blob(tag, PERSON, CLUB, CLUB_UID)
            hit = self.emt.discover_managed_club(blob, len(blob))
            self.assertIsNotNone(hit)
            assert hit is not None
            self.assertEqual(hit["clubId"], CLUB_UID)
            self.assertEqual(hit["clubNameShort"], CLUB)
            self.assertEqual(hit["tagHex"], tag.hex())

    def test_continue_tag_still_resolves_club(self) -> None:
        blob = _identity_blob(TAG_02, PERSON, CLUB, CLUB_UID)
        a = self.emt.discover_managed_club(blob, len(blob))
        b = self.eft.discover_managed_club(blob, len(blob))
        self.assertEqual(a, b)
        self.assertEqual(a["clubId"], CLUB_UID)

    def test_later_calendar_table_is_not_today(self) -> None:
        ident = _identity_blob(TAG_01, PERSON, CLUB, CLUB_UID) + struct.pack(
            "<BBH", 0, TODAY.timetuple().tm_yday, TODAY.year
        )
        blob = (
            ident
            + _prelude(self.emt, TODAY)
            + _today_ptr(TODAY)
            + b"\x00" * 64
            + _table(self.emt, TABLE_END)
        )
        hit = self.emt.discover_managed_club(blob, len(blob))
        self.assertIsNotNone(hit)
        picked = self.emt.pick_game_date_near_identity(blob, hit)
        self.assertIsNotNone(picked)
        assert picked is not None
        self.assertEqual(picked["gameDate"], TODAY.isoformat())
        self.assertNotEqual(picked["gameDate"], TABLE_END.isoformat())
        self.assertEqual(picked["method"], "uniqueid_tail_doy_year")
        table_isos = {
            c["iso"] for c in picked["candidates"] if c["kind"] == "prelude"
        }
        self.assertIn(TABLE_END.isoformat(), table_isos)

    def test_only_calendar_table_is_unsure_not_a_year(self) -> None:
        ident = _identity_blob(TAG_02, PERSON, CLUB, CLUB_UID)
        blob = ident + b"\x00" * 32 + _table(self.emt, TABLE_END)
        hit = self.emt.discover_managed_club(blob, len(blob))
        self.assertIsNotNone(hit)
        picked = self.emt.pick_game_date_near_identity(blob, hit)
        self.assertIsNotNone(picked)
        assert picked is not None
        self.assertIsNone(picked["gameDate"])
        self.assertEqual(picked["method"], "identity_unsure")
        self.assertNotEqual(picked.get("gameDate"), TABLE_END.isoformat())

    def test_two_today_ptr_days_do_not_pick_the_later_table(self) -> None:
        ident = _identity_blob(TAG_01, PERSON, CLUB, CLUB_UID) + struct.pack(
            "<BBH", 0, TODAY.timetuple().tm_yday, TODAY.year
        )
        blob = (
            ident
            + _prelude(self.emt, TODAY)
            + _today_ptr(TODAY)
            + _table(self.emt, TABLE_END)
            + _today_ptr(TABLE_END)
        )
        hit = self.emt.discover_managed_club(blob, len(blob))
        picked = self.emt.pick_game_date_near_identity(blob, hit)
        self.assertIsNotNone(picked)
        assert picked is not None
        self.assertNotEqual(picked.get("gameDate"), TABLE_END.isoformat())
        if picked.get("gameDate") is not None:
            self.assertEqual(picked["gameDate"], TODAY.isoformat())


if __name__ == "__main__":
    unittest.main()
