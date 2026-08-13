"""T008: gap UIDs resolve real names (Risse must not be uid:)."""

from __future__ import annotations

import importlib.util
import json
import mmap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tmp" / "live-0112-decomp.bin"
FIXTURE = ROOT / "data" / "fixtures" / "person-name-mark-locked.json"

RISSE_UID = 2002217460


def _load_eft():
    spec = importlib.util.spec_from_file_location(
        "eft_t008", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(BIN.is_file() and FIXTURE.is_file(), "live-0112 / name fixture missing")
class TestRosterNameResolutionT008(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.lock = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.eft = _load_eft()
        cls.mm_file = BIN.open("rb")
        cls.mm = mmap.mmap(cls.mm_file.fileno(), 0, access=mmap.ACCESS_READ)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.mm.close()
        cls.mm_file.close()

    def test_fixture_offsets_match_module(self) -> None:
        self.assertEqual(
            bytes.fromhex(self.lock["mark"]), self.eft.PERSON_NAME_MARK
        )
        self.assertEqual(
            self.lock["firstNameIdOffset"], self.eft.PERSON_NAME_FIRST_OFF
        )
        self.assertEqual(
            self.lock["secondNameIdOffset"], self.eft.PERSON_NAME_SECOND_OFF
        )
        self.assertEqual(self.lock["nameTableBand"]["lo"], self.eft.NAME_TABLE_LO)
        self.assertEqual(self.lock["nameTableBand"]["hi"], self.eft.NAME_TABLE_HI)

    def test_risse_not_uid_fallback(self) -> None:
        doubles = self.eft.collect_doubles(self.mm, RISSE_UID)
        name = self.eft.resolve_name(self.mm, RISSE_UID, doubles)
        self.assertEqual(name, "Landri Risse")
        self.assertFalse(name.startswith("uid:"))

    def test_gap_uids_from_fixture(self) -> None:
        for uid_s, row in self.lock["expected"].items():
            uid = int(uid_s)
            doubles = self.eft.collect_doubles(self.mm, uid)
            name = self.eft.resolve_name(self.mm, uid, doubles)
            self.assertEqual(name, row["name"], msg=f"uid={uid}")
            self.assertFalse(name.startswith("uid:"), msg=f"uid={uid}")

    def test_mark_path_required_for_risse(self) -> None:
        """Risse has zero \\x00\\x02+uid inline names — mark join is the path."""
        pat = b"\x00\x02" + __import__("struct").pack("<I", RISSE_UID)
        self.assertEqual(self.mm.find(pat), -1)
        doubles = self.eft.collect_doubles(self.mm, RISSE_UID)
        marked = self.eft.resolve_name_from_mark(self.mm, RISSE_UID, doubles)
        self.assertEqual(marked, "Landri Risse")


if __name__ == "__main__":
    unittest.main()
