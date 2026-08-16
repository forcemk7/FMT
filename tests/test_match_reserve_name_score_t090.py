"""T090: match_reserve_name_score is defined and scores II / B / U21 without raising."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class MatchReserveNameScoreT090Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ii = _load("ii_t090", ROOT / "scripts" / "ii_squad_discovery.py")

    def test_import_match_reserve_name_score(self) -> None:
        self.assertTrue(callable(self.ii.match_reserve_name_score))

    def test_scores_ii_b_u21_without_raising(self) -> None:
        parent = "Sample Town"
        for name in (f"{parent} II", f"{parent} B", f"{parent} U21"):
            score = self.ii.match_reserve_name_score(parent, name)
            self.assertGreaterEqual(score, 70, msg=name)
            self.assertEqual(score, self.ii.match_unit_core_score(parent, parent))

    def test_no_reserve_suffix_is_zero(self) -> None:
        self.assertEqual(self.ii.match_reserve_name_score("Sample Town", "Sample Town"), 0)


if __name__ == "__main__":
    unittest.main()
