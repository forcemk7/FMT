"""T114: Native clubIdAbs+488 namelist → Squad (unit list); continue skips +488."""

from __future__ import annotations

import importlib.util
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG_NATIVE = bytes.fromhex("00950e01")
TAG_CONTINUE = bytes.fromhex("00950e02")
CLUB_ID_NAMELIST_REL = 488


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _lp32(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack("<I", len(raw)) + raw


def _identity(tag: bytes, uid: int, club: str) -> bytes:
    return tag + _lp32("Pat Example") + _lp32(club) + struct.pack("<I", uid)


def _namelist(names: list[str]) -> bytes:
    return struct.pack("<I", len(names)) + b"".join(_lp32(n) for n in names)


def _native_blob(uid: int, club: str, names: list[str]) -> bytes:
    ident = _identity(TAG_NATIVE, uid, club)
    club_id_abs = len(ident) - 4
    # Count sits at clubIdAbs+488 (UniqueID is the first 4 of that span).
    pad = (club_id_abs + CLUB_ID_NAMELIST_REL) - len(ident)
    return ident + bytes(pad) + _namelist(names) + bytes(32)


class NativeNamelistMvpT114Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("esl_t114", ROOT / "scripts" / "extract-squad-lists.py")

    def test_method_is_plus488_not_senior_object(self) -> None:
        src = (ROOT / "scripts" / "extract-squad-lists.py").read_text(encoding="utf-8")
        self.assertIn("native-clubid-plus488-v1", src)
        self.assertIn("CLUB_ID_NAMELIST_REL = 488", src)
        self.assertNotIn("senior-squad-object-v1", src)
        self.assertNotIn("extract-first-team-fast.py", src)
        self.assertFalse(hasattr(self.mod, "resolve_ft_squad"))
        self.assertTrue(hasattr(self.mod, "parse_club_id_plus488_namelist"))

    def test_liverpool_style_count_35(self) -> None:
        names = [f"Player {i}" for i in range(35)]
        names[0] = "Alisson"
        names[1] = "Frimpong"
        names[2] = "Leoni"
        blob = _native_blob(676, "Liverpool", names)
        result = self.mod.extract_from_mmap(blob, save=Path("synthetic-liv.fm"), t0=0.0)
        self.assertEqual(len(result["players"]), 35)
        self.assertEqual(result["countHeader"], 35)
        self.assertEqual(result["discovery"]["countHeader"], 35)
        self.assertEqual(result["discovery"]["method"], "native-clubid-plus488-v1")
        self.assertEqual(result["players"][0]["name"], "Alisson")
        self.assertEqual(result["players"][0]["_extract"]["unit"], "list")
        self.assertNotEqual(result["players"][0]["_extract"]["unit"], "Senior")
        self.assertFalse(result["players"][0]["_extract"]["uidResolved"])

    def test_bournemouth_style_count_33_different(self) -> None:
        names = [f"Cherries {i}" for i in range(33)]
        names[0] = "Petrovic"
        blob = _native_blob(600, "Bournemouth", names)
        result = self.mod.extract_from_mmap(blob, save=Path("synthetic-bou.fm"), t0=0.0)
        self.assertEqual(len(result["players"]), 33)
        self.assertEqual(result["countHeader"], 33)
        self.assertEqual(result["clubId"], 600)
        self.assertEqual(result["players"][0]["name"], "Petrovic")
        self.assertEqual(result["discovery"]["unitLabel"], "list")

    def test_continue_does_not_use_plus488(self) -> None:
        ident = _identity(TAG_CONTINUE, 790, "FC Schalke 04")
        club_id_abs = len(ident) - 4
        pad = (club_id_abs + CLUB_ID_NAMELIST_REL) - len(ident)
        names = [f"Trap {i}" for i in range(20)]
        blob = ident + bytes(pad) + _namelist(names) + bytes(32)
        result = self.mod.extract_from_mmap(blob, save=Path("synthetic-cont.fm"), t0=0.0)
        self.assertEqual(result["players"], [])
        self.assertEqual(
            result["discovery"]["missReason"],
            "continue-skip-native-plus488",
        )
        self.assertEqual(result["discovery"]["unitStatus"]["list"], "skipped-continue")

    def test_parse_helper_matches_in_file_count(self) -> None:
        names = ["One", "Two", "Three"]
        blob = _native_blob(1, "Sample", names)
        id_off = len(_identity(TAG_NATIVE, 1, "Sample")) - 4
        hit = self.mod.parse_club_id_plus488_namelist(blob, id_off)
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit["countHeader"], 3)
        self.assertEqual(hit["names"], names)
        self.assertEqual(hit["listAbs"], id_off + CLUB_ID_NAMELIST_REL)


if __name__ == "__main__":
    unittest.main()
