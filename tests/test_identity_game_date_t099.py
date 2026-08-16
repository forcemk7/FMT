"""T099: UniqueID-tail u16 doy + u16 year — not u8 doy, not day/month."""

from __future__ import annotations

import importlib.util
import struct
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TAG_01 = bytes.fromhex("00950e01")
PERSON = "Pat Example"
CLUB = "Sample Town"
CLUB_UID = 4242


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _lp32(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack("<I", len(raw)) + raw


def _identity_blob(uid: int, *, tail: bytes) -> bytes:
    return TAG_01 + _lp32(PERSON) + _lp32(CLUB) + struct.pack("<I", uid) + tail


class IdentityGameDateT099Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.emt = _load("emt_t099", ROOT / "scripts" / "extract-managed-team.py")
        cls.src = (ROOT / "scripts" / "extract-managed-team.py").read_text(
            encoding="utf-8"
        )

    def _pick(self, tail: bytes) -> dict:
        blob = _identity_blob(CLUB_UID, tail=tail)
        hit = self.emt.discover_managed_club(blob, len(blob))
        self.assertIsNotNone(hit)
        picked = self.emt.pick_game_date_near_identity(blob, hit)
        self.assertIsNotNone(picked)
        assert picked is not None
        return picked

    def test_u8_tail_index_doy_is_gone(self) -> None:
        self.assertNotIn("tail_bytes[1]", self.src)

    def test_pack_hh_4_2026_is_4_jan(self) -> None:
        picked = self._pick(struct.pack("<HH", 4, 2026))
        self.assertEqual(picked["gameDate"], date(2026, 1, 4).isoformat())
        self.assertEqual(picked["doy"], 4)
        self.assertEqual(picked["year"], 2026)

    def test_pack_hh_0404_2026_is_4_jan_not_4_apr(self) -> None:
        picked = self._pick(struct.pack("<HH", 0x0404, 2026))
        self.assertEqual(picked["gameDate"], date(2026, 1, 4).isoformat())
        self.assertNotEqual(picked["gameDate"], date(2026, 4, 4).isoformat())
        self.assertEqual(picked["doy"], 0x0404 & 0x1FF)
        self.assertEqual(picked["year"], 2026)

    def test_pack_hh_363_2025_is_29_dec_not_1_jan_or_17_apr(self) -> None:
        picked = self._pick(struct.pack("<HH", 363, 2025))
        want = date(2025, 1, 1) + timedelta(days=362)
        self.assertEqual(want, date(2025, 12, 29))
        self.assertEqual(picked["gameDate"], want.isoformat())
        self.assertNotEqual(picked["gameDate"], date(2025, 1, 1).isoformat())
        self.assertNotEqual(picked["gameDate"], date(2025, 4, 17).isoformat())
        self.assertEqual(picked["doy"], 363)
        self.assertEqual(picked["year"], 2025)

    def test_pack_hh_1_2026_is_1_jan(self) -> None:
        picked = self._pick(struct.pack("<HH", 1, 2026))
        self.assertEqual(picked["gameDate"], date(2026, 1, 1).isoformat())
        self.assertEqual(picked["doy"], 1)
        self.assertEqual(picked["year"], 2026)


if __name__ == "__main__":
    unittest.main()
