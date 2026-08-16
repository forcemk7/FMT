"""T106: continue tag 02 gameDate from UniqueID trailer (rolling-stack lock)."""

from __future__ import annotations

import importlib.util
import struct
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TAG_01 = bytes.fromhex("00950e01")
TAG_02 = bytes.fromhex("00950e02")
PERSON = "Pat Example"
CLUB = "Sample Town"
CLUB_UID = 4242
TWIN = 0x11111111
DAY_A = date(2040, 10, 15)
DAY_B = date(2040, 10, 24)
NATIVE_DAY = date(2026, 1, 4)
CAL_LIE = date(2040, 1, 13)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _lp32(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack("<I", len(raw)) + raw


def _date_hh(d: date, *, raw: int | None = None) -> bytes:
    doy = d.timetuple().tm_yday if raw is None else raw
    return struct.pack("<HH", doy if raw is None else raw, d.year)


def _continue_after_uid(d: date, *, label: str = "Pad Label", raw: int | None = None) -> bytes:
    return _lp32(label) + struct.pack("<II", 0, 0xFFFFFFFF) + _date_hh(d, raw=raw)


def _identity(tag: bytes, *, after_uid: bytes = b"") -> bytes:
    return tag + _lp32(PERSON) + _lp32(CLUB) + struct.pack("<I", CLUB_UID) + after_uid


def _prelude(mod, d: date) -> bytes:
    days = (d - date(1900, 1, 1)).days
    return mod.GAME_DATE_PRELUDE + struct.pack("<III", days, TWIN, TWIN)


def _today_ptr(d: date) -> bytes:
    n = (d - date(1900, 1, 1)).days
    return struct.pack("<II", n - 1, n) + b"\x00\x00\x00\x00"


class ContinueUidTrailerDateT106Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.emt = _load("emt_t106", ROOT / "scripts" / "extract-managed-team.py")

    def _pick(self, blob: bytes) -> dict:
        hit = self.emt.discover_managed_club(blob, len(blob))
        self.assertIsNotNone(hit)
        picked = self.emt.pick_game_date_near_identity(blob, hit)
        self.assertIsNotNone(picked)
        assert picked is not None
        return picked

    def test_trailer_plain_doy_year(self) -> None:
        picked = self._pick(_identity(TAG_02, after_uid=_continue_after_uid(DAY_A)))
        self.assertEqual(picked["gameDate"], DAY_A.isoformat())
        self.assertEqual(picked["method"], "continue_uid_trailer_doy_year")
        self.assertEqual(picked["doy"], DAY_A.timetuple().tm_yday)
        self.assertEqual(picked["year"], DAY_A.year)

    def test_trailer_masked_raw_doy(self) -> None:
        """raw > 366 → doy = raw & 0x1FF (same as T099)."""
        doy = DAY_B.timetuple().tm_yday
        raw = doy | 0x8900
        self.assertGreater(raw, 366)
        self.assertEqual(raw & 0x1FF, doy)
        picked = self._pick(
            _identity(TAG_02, after_uid=_continue_after_uid(DAY_B, raw=raw))
        )
        self.assertEqual(picked["gameDate"], DAY_B.isoformat())
        self.assertEqual(picked["doy"], doy)

    def test_stack_day_step_moves_trailer_only(self) -> None:
        a = self._pick(_identity(TAG_02, after_uid=_continue_after_uid(DAY_A)))
        b = self._pick(_identity(TAG_02, after_uid=_continue_after_uid(DAY_B)))
        self.assertEqual(a["gameDate"], DAY_A.isoformat())
        self.assertEqual(b["gameDate"], DAY_B.isoformat())
        self.assertNotEqual(a["gameDate"], b["gameDate"])

    def test_calendar_today_ptr_is_not_picked(self) -> None:
        blob = (
            _identity(TAG_02, after_uid=_continue_after_uid(DAY_A))
            + _prelude(self.emt, CAL_LIE)
            + _today_ptr(CAL_LIE)
        )
        picked = self._pick(blob)
        self.assertEqual(picked["gameDate"], DAY_A.isoformat())
        self.assertNotEqual(picked["gameDate"], CAL_LIE.isoformat())

    def test_native_uniqueid_plus4_still_t099(self) -> None:
        blob = _identity(TAG_01, after_uid=_date_hh(NATIVE_DAY))
        picked = self._pick(blob)
        self.assertEqual(picked["gameDate"], NATIVE_DAY.isoformat())
        self.assertEqual(picked["method"], "uniqueid_tail_doy_year")

    def test_missing_sentinel_is_unsure(self) -> None:
        bad = _lp32("Pad Label") + struct.pack("<II", 0, 0) + _date_hh(DAY_A)
        picked = self._pick(_identity(TAG_02, after_uid=bad))
        self.assertIsNone(picked["gameDate"])
        self.assertEqual(picked["method"], "identity_unsure")

    def test_no_hardcoded_konig_iso_in_source(self) -> None:
        src = (ROOT / "scripts" / "extract-managed-team.py").read_text(encoding="utf-8")
        self.assertNotIn("2040-10-24", src)
        self.assertNotIn("2040-10-15", src)
        self.assertNotIn("New Gan", src)
        self.assertNotIn("Schalke", src)


if __name__ == "__main__":
    unittest.main()
