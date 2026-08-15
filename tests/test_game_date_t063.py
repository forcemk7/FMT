"""T063/T064: extract gameDate is the blob today marker, never filename."""

from __future__ import annotations

import importlib.util
import struct
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "extract_ft", ROOT / "scripts" / "extract-first-team-fast.py"
)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)

TWIN = 0x11111111
DATED_SAVE = Path(
    "FC Schalke 04 - Bastian Koenig - FM24Career (In-game date 19.11.2039).fm"
)


def _days(d: date) -> int:
    return (d - mod.DATE_EPOCH).days


def _prelude(d: date) -> bytes:
    return mod.GAME_DATE_PRELUDE + struct.pack("<III", _days(d), TWIN, TWIN)


def _today_ptr(d: date) -> bytes:
    n = _days(d)
    return struct.pack("<II", n - 1, n) + b"\x00\x00\x00\x00"


def _july_cluster_plus_later(later: date) -> bytes:
    """Pre-season every-other-day ptrs (dense window) plus one later today_ptr."""
    chunks: list[bytes] = []
    july1 = date(2039, 7, 1)
    for i in range(27):
        chunks.append(_prelude(date(2039, 6, 30) + timedelta(days=i)))
    for i in range(0, 25, 2):
        chunks.append(_today_ptr(july1 + timedelta(days=i)))
    chunks.append(_prelude(later))
    chunks.append(_today_ptr(later))
    return b"".join(chunks)


class GameDateT063Tests(unittest.TestCase):
    def test_no_hint_picks_latest_today_ptr_not_july_cluster(self):
        later = date(2039, 12, 1)
        buf = _july_cluster_plus_later(later)
        got = mod.discover_game_date(buf)
        self.assertIsNotNone(got)
        self.assertEqual(got["gameDate"], "2039-12-01")
        self.assertEqual(got["method"], "today_ptr_latest")

    def test_later_save_moves_game_date(self):
        d1 = mod.discover_game_date(_july_cluster_plus_later(date(2039, 12, 1)))
        d2 = mod.discover_game_date(_july_cluster_plus_later(date(2040, 1, 13)))
        self.assertEqual(d1["gameDate"], "2039-12-01")
        self.assertEqual(d2["gameDate"], "2040-01-13")
        self.assertNotEqual(d1["gameDate"], d2["gameDate"])


class GameDateT067Tests(unittest.TestCase):
    def test_walks_consecutive_prelude_after_sparse_today_ptr(self):
        """today_ptr stuck on D1 + prelude D1..D1+2 → in-game today is D1+2."""
        d1 = date(2040, 1, 13)
        buf = _july_cluster_plus_later(d1)
        buf += _prelude(d1 + timedelta(days=1))
        buf += _prelude(d1 + timedelta(days=2))
        got = mod.discover_game_date(buf)
        self.assertEqual(got["gameDate"], "2040-01-15")
        self.assertEqual(got["method"], "calendar_run_end")

    def test_gapped_fixture_prelude_does_not_jump(self):
        """Jan 22 fixture after Jan 13 today_ptr is not today."""
        d1 = date(2040, 1, 13)
        buf = _july_cluster_plus_later(d1)
        buf += _prelude(date(2040, 1, 22))
        buf += _prelude(date(2040, 2, 5))
        got = mod.discover_game_date(buf)
        self.assertEqual(got["gameDate"], "2040-01-13")
        self.assertEqual(got["method"], "today_ptr_latest")

    def test_later_today_ptr_without_prelude_is_not_today(self):
        """Fixture/news (d-1,d,0) pairs exist through 2042; only prelude-gated ptrs are today."""
        d1 = date(2040, 1, 13)
        mar7 = date(2040, 3, 7)
        buf = _july_cluster_plus_later(d1) + _today_ptr(mar7)
        got = mod.discover_game_date(buf)
        self.assertEqual(got["gameDate"], "2040-01-13")
        self.assertEqual(got["method"], "today_ptr_latest")

    def test_second_save_moves_when_calendar_run_extends(self):
        d1 = date(2040, 1, 13)
        d2 = date(2040, 1, 14)
        first = mod.discover_game_date(_july_cluster_plus_later(d1))
        second_buf = _july_cluster_plus_later(d1) + _prelude(d2)
        second = mod.discover_game_date(second_buf)
        self.assertEqual(first["gameDate"], "2040-01-13")
        self.assertEqual(second["gameDate"], "2040-01-14")
        self.assertNotEqual(first["gameDate"], second["gameDate"])


class GameDateT064Tests(unittest.TestCase):
    def test_dated_filename_does_not_override_later_blob(self):
        """(In-game date 19.11.2039).fm whose blob today is 2040-01-13 → blob."""
        self.assertEqual(mod.parse_save_game_date_hint(DATED_SAVE), date(2039, 11, 19))
        buf = _july_cluster_plus_later(date(2040, 1, 13))
        got = mod.discover_game_date(buf, hint=mod.parse_save_game_date_hint(DATED_SAVE))
        self.assertEqual(got["gameDate"], "2040-01-13")
        self.assertEqual(got["method"], "today_ptr_latest")
        self.assertIsNone(got["hint"])

    def test_career_fm_same_blob_date(self):
        self.assertIsNone(mod.parse_save_game_date_hint(Path("Career.fm")))
        buf = _july_cluster_plus_later(date(2040, 1, 13))
        dated = mod.discover_game_date(
            buf, hint=mod.parse_save_game_date_hint(DATED_SAVE)
        )
        fixed = mod.discover_game_date(buf, hint=None)
        self.assertEqual(dated["gameDate"], "2040-01-13")
        self.assertEqual(fixed["gameDate"], dated["gameDate"])


if __name__ == "__main__":
    unittest.main()
