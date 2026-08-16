"""T097: UniqueID-tail doy+year — not day/month, not 24MB calendar."""

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
TABLE_END = date(2038, 5, 25)
# Synthetic packing of the owner-confirmed tail 04 04 ea 07 — not a fitted save.
PACKED_JAN4 = bytes.fromhex("0404ea07")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _lp32(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack("<I", len(raw)) + raw


def _date_tail(d: date) -> bytes:
    return struct.pack("<HH", d.timetuple().tm_yday, d.year)


def _identity_blob(
    tag: bytes,
    person: str,
    club: str,
    uid: int,
    *,
    tail: bytes | None = None,
) -> bytes:
    body = tag + _lp32(person) + _lp32(club) + struct.pack("<I", uid)
    if tail is not None:
        body += tail
    return body


def _days(d: date) -> int:
    return (d - date(1900, 1, 1)).days


def _prelude(mod, d: date) -> bytes:
    return mod.GAME_DATE_PRELUDE + struct.pack("<III", _days(d), TWIN, TWIN)


def _table(mod, end: date, n: int = 10) -> bytes:
    start = end - timedelta(days=n - 1)
    return b"".join(_prelude(mod, start + timedelta(days=i)) for i in range(n))


class IdentityGameDateT097Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.emt = _load("emt_t097", ROOT / "scripts" / "extract-managed-team.py")

    def test_uniqueid_tail_doy_year_is_that_calendar_day(self) -> None:
        want = date(2026, 8, 16)
        blob = _identity_blob(TAG_01, PERSON, CLUB, CLUB_UID, tail=_date_tail(want))
        hit = self.emt.discover_managed_club(blob, len(blob))
        self.assertIsNotNone(hit)
        picked = self.emt.pick_game_date_near_identity(blob, hit)
        self.assertIsNotNone(picked)
        assert picked is not None
        self.assertEqual(picked["gameDate"], want.isoformat())
        self.assertEqual(picked["method"], "uniqueid_tail_doy_year")
        self.assertEqual(picked["doy"], want.timetuple().tm_yday)
        self.assertEqual(picked["year"], want.year)

    def test_packed_0404ea07_is_4_jan_not_4_apr(self) -> None:
        blob = _identity_blob(TAG_01, PERSON, CLUB, CLUB_UID, tail=PACKED_JAN4)
        hit = self.emt.discover_managed_club(blob, len(blob))
        picked = self.emt.pick_game_date_near_identity(blob, hit)
        self.assertIsNotNone(picked)
        assert picked is not None
        self.assertEqual(picked["doy"], PACKED_JAN4[1])
        self.assertEqual(picked["year"], struct.unpack_from("<H", PACKED_JAN4, 2)[0])
        jan4 = date(picked["year"], 1, 1) + timedelta(days=picked["doy"] - 1)
        self.assertEqual(picked["gameDate"], jan4.isoformat())
        self.assertEqual(jan4, date(2026, 1, 4))
        self.assertNotEqual(picked["gameDate"], date(2026, 4, 4).isoformat())

    def test_later_calendar_table_is_not_picked(self) -> None:
        want = date(2026, 1, 4)
        ident = _identity_blob(
            TAG_01, PERSON, CLUB, CLUB_UID, tail=_date_tail(want)
        )
        blob = ident + _table(self.emt, TABLE_END)
        hit = self.emt.discover_managed_club(blob, len(blob))
        picked = self.emt.pick_game_date_near_identity(blob, hit)
        self.assertIsNotNone(picked)
        assert picked is not None
        self.assertEqual(picked["gameDate"], want.isoformat())
        self.assertNotEqual(picked["gameDate"], TABLE_END.isoformat())

    def test_invalid_doy_year_is_dash(self) -> None:
        blob = _identity_blob(
            TAG_02, PERSON, CLUB, CLUB_UID, tail=struct.pack("<HH", 0, 2026)
        )
        hit = self.emt.discover_managed_club(blob, len(blob))
        picked = self.emt.pick_game_date_near_identity(blob, hit)
        self.assertIsNotNone(picked)
        assert picked is not None
        self.assertIsNone(picked["gameDate"])
        self.assertEqual(picked["method"], "identity_unsure")

    def test_year_out_of_range_is_dash(self) -> None:
        blob = _identity_blob(
            TAG_01, PERSON, CLUB, CLUB_UID, tail=struct.pack("<HH", 4, 1999)
        )
        hit = self.emt.discover_managed_club(blob, len(blob))
        picked = self.emt.pick_game_date_near_identity(blob, hit)
        self.assertIsNone(picked["gameDate"])

    def test_no_hardcoded_inspect_iso_in_source(self) -> None:
        src = (ROOT / "scripts" / "extract-managed-team.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("2026-01-04", src)
        self.assertNotIn("Liverpool", src)


if __name__ == "__main__":
    unittest.main()
