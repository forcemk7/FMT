"""T114 +488 MVP — superseded by T118 club .dat Senior UniqueIDs."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "esl_t114", ROOT / "scripts" / "extract-squad-lists.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class NativeNamelistMvpT114SupersededTests(unittest.TestCase):
    def test_plus488_replaced_by_club_dat_senior(self) -> None:
        src = (ROOT / "scripts" / "extract-squad-lists.py").read_text(encoding="utf-8")
        self.assertIn("native-club-dat-senior-v1", src)
        self.assertNotIn("native-clubid-plus488-v1", src)
        self.assertNotIn("CLUB_ID_NAMELIST_REL = 488", src)
        mod = _load()
        self.assertTrue(hasattr(mod, "players_from_club_dat"))
        self.assertFalse(hasattr(mod, "parse_club_id_plus488_namelist"))


if __name__ == "__main__":
    unittest.main()
