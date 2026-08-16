"""T101 + T106: tag 01 UniqueID-tail; tag 02 continue UniqueID trailer — never calendar."""

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
TAIL_DAY = date(2026, 1, 4)
CAL_DAY = date(2026, 8, 16)
TRAILER_DAY = date(2040, 10, 24)


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


def _continue_trailer(d: date, *, label: str = "Pad Label", raw: int | None = None) -> bytes:
    """UniqueID already in identity blob; this is the bytes after UniqueID."""
    doy = d.timetuple().tm_yday if raw is None else raw
    return (
        _lp32(label)
        + struct.pack("<II", 0, 0xFFFFFFFF)
        + struct.pack("<HH", doy if raw is None else raw, d.year)
    )


def _identity_blob(tag: bytes, *, after_uid: bytes | None = None) -> bytes:
    body = tag + _lp32(PERSON) + _lp32(CLUB) + struct.pack("<I", CLUB_UID)
    if after_uid is not None:
        body += after_uid
    return body


def _days(d: date) -> int:
    return (d - date(1900, 1, 1)).days


def _prelude(mod, d: date) -> bytes:
    return mod.GAME_DATE_PRELUDE + struct.pack("<III", _days(d), TWIN, TWIN)


def _today_ptr(d: date) -> bytes:
    n = _days(d)
    return struct.pack("<II", n - 1, n) + b"\x00\x00\x00\x00"


class IdentityGameDateT101Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.emt = _load("emt_t101", ROOT / "scripts" / "extract-managed-team.py")

    def _pick(self, blob: bytes) -> dict:
        hit = self.emt.discover_managed_club(blob, len(blob))
        self.assertIsNotNone(hit)
        picked = self.emt.pick_game_date_near_identity(blob, hit)
        self.assertIsNotNone(picked)
        assert picked is not None
        return picked

    def test_native_tag_01_still_uniqueid_tail(self) -> None:
        blob = (
            _identity_blob(TAG_01, after_uid=_date_tail(TAIL_DAY))
            + _prelude(self.emt, CAL_DAY)
            + _today_ptr(CAL_DAY)
        )
        picked = self._pick(blob)
        self.assertEqual(picked["gameDate"], TAIL_DAY.isoformat())
        self.assertNotEqual(picked["gameDate"], CAL_DAY.isoformat())
        self.assertEqual(picked["method"], "uniqueid_tail_doy_year")
        self.assertEqual(picked["doy"], TAIL_DAY.timetuple().tm_yday)
        self.assertEqual(picked["year"], TAIL_DAY.year)

    def test_continue_tag_02_uses_trailer_not_uniqueid_tail(self) -> None:
        blob = (
            _identity_blob(TAG_02, after_uid=_continue_trailer(TRAILER_DAY))
            + _date_tail(TAIL_DAY)  # decoy if mis-aligned
            + _prelude(self.emt, CAL_DAY)
            + _today_ptr(CAL_DAY)
        )
        picked = self._pick(blob)
        self.assertEqual(picked["gameDate"], TRAILER_DAY.isoformat())
        self.assertNotEqual(picked["gameDate"], TAIL_DAY.isoformat())
        self.assertNotEqual(picked["gameDate"], CAL_DAY.isoformat())
        self.assertEqual(picked["method"], "continue_uid_trailer_doy_year")
        self.assertEqual(picked["doy"], TRAILER_DAY.timetuple().tm_yday)
        self.assertEqual(picked["year"], TRAILER_DAY.year)

    def test_continue_tag_02_without_trailer_is_dash_even_with_native_tail(self) -> None:
        blob = _identity_blob(TAG_02, after_uid=_date_tail(TAIL_DAY))
        picked = self._pick(blob)
        self.assertIsNone(picked["gameDate"])
        self.assertEqual(picked["method"], "identity_unsure")

    def test_continue_ignores_calendar_run_without_trailer(self) -> None:
        end = CAL_DAY + timedelta(days=2)
        blob = (
            _identity_blob(TAG_02)
            + _prelude(self.emt, CAL_DAY)
            + _prelude(self.emt, CAL_DAY + timedelta(days=1))
            + _prelude(self.emt, end)
            + _today_ptr(CAL_DAY)
        )
        picked = self._pick(blob)
        self.assertIsNone(picked["gameDate"])
        self.assertEqual(picked["method"], "identity_unsure")


if __name__ == "__main__":
    unittest.main()
