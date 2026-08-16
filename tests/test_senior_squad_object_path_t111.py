"""T111 archived expectations — extract path superseded by T114 (+488 namelist)."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SeniorSquadObjectPathT111Superseded(unittest.TestCase):
    def test_t114_replaced_senior_object_extract(self) -> None:
        src = (ROOT / "scripts" / "extract-squad-lists.py").read_text(encoding="utf-8")
        self.assertIn("native-clubid-plus488-v1", src)
        self.assertNotIn("senior-squad-object-v1", src)


if __name__ == "__main__":
    unittest.main()
