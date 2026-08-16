"""T111: Senior Squad object path — no T110 namelist; honest miss when no squad object."""

from __future__ import annotations

import importlib.util
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG_NATIVE = bytes.fromhex("00950e01")
TAG_CONTINUE = bytes.fromhex("00950e02")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _lp32(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack("<I", len(raw)) + raw


def _identity(tag: bytes, uid: int, club: str = "Sample Town") -> bytes:
    return tag + _lp32("Pat Example") + _lp32(club) + struct.pack("<I", uid)


class SeniorSquadObjectPathT111Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("esl_t111", ROOT / "scripts" / "extract-squad-lists.py")

    def test_no_t110_namelist_helpers(self) -> None:
        self.assertFalse(hasattr(self.mod, "find_native_identity_namelist"))
        self.assertFalse(hasattr(self.mod, "canonical_ft_names"))
        src = (ROOT / "scripts" / "extract-squad-lists.py").read_text(encoding="utf-8")
        self.assertIn("senior-squad-object-v1", src)
        self.assertIn("T110 identity-neighborhood namelist", src)
        self.assertNotIn("NAME_LIST_WINDOW", src)

    def test_native_identity_without_squad_object_is_honest_miss(self) -> None:
        # Identity only — pad must NOT be treated as a namelist.
        names = [
            "Alisson",
            "Virgil van Dijk",
            "Mohamed Salah",
            "Cody Gakpo",
            "Dominik Szoboszlai",
            "Alexis Mac Allister",
            "Jeremie Frimpong",
            "Miloš Kerkez",
            "Alexander Isak",
            "Rio Ngumoha",
            "Trey Nyoni",
            "J. Frimpong",
        ]
        namelist = struct.pack("<I", len(names)) + b"".join(_lp32(n) for n in names)
        blob = _identity(TAG_NATIVE, 676, "Liverpool") + bytes(488) + namelist + bytes(64)
        result = self.mod.extract_from_mmap(blob, save=Path("synthetic-native.fm"), t0=0.0)
        self.assertEqual(result["players"], [])
        disc = result["discovery"]
        self.assertEqual(disc["method"], "senior-squad-object-v1")
        self.assertEqual(disc["missReason"], "senior-squad-object-miss")
        self.assertIn("objectPath", disc)
        self.assertEqual(disc["unitStatus"]["Senior"], "miss")
        # Must not invent a count from the planted namelist.
        self.assertNotIn("ftCanonical", disc)
        self.assertNotIn("rawCount", disc)

    def test_continue_without_squad_object_is_honest_miss(self) -> None:
        blob = _identity(TAG_CONTINUE, 790, "FC Schalke 04") + bytes(1024)
        result = self.mod.extract_from_mmap(blob, save=Path("synthetic-continue.fm"), t0=0.0)
        self.assertEqual(result["players"], [])
        self.assertEqual(
            result["discovery"]["missReason"],
            "continue-senior-squad-object-miss",
        )


if __name__ == "__main__":
    unittest.main()
