"""T076: club identity skips all-club 7f02 + staff-link ranking."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_eft():
    spec = importlib.util.spec_from_file_location(
        "eft_t076", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


class TestWorldListsSkipT076(unittest.TestCase):
    def test_known_club_does_not_walk_world_lists(self) -> None:
        eft = _load_eft()
        squads, hits, kind = eft.walk_world_squads_if_needed(
            None,
            club_short="Schalke 04",
            squads={},
            manager_hits={},
        )
        self.assertEqual(kind, "skipped_identity_known")
        self.assertEqual(squads, {})
        self.assertEqual(hits, {})


if __name__ == "__main__":
    unittest.main()
