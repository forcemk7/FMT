"""T110: native identity namelist → FT names (synthetic structural tests)."""

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


def _namelist(names: list[str]) -> bytes:
    body = b"".join(_lp32(n) for n in names)
    return struct.pack("<I", len(names)) + body


class NativeIdentityNamelistT110Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("esl_t110", ROOT / "scripts" / "extract-squad-lists.py")

    def test_finds_count_then_names_after_identity(self) -> None:
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
            "V. van Dijk",
            "M. Salah",
            "A. Robertson",
            "R. Gravenberch",
        ]
        ident = _identity(TAG_NATIVE, 676, "Liverpool")
        # Pad to ~520 bytes after identity start (matches native delta band).
        pad = bytes(500)
        blob = ident + pad + _namelist(names) + bytes(64)
        identity_abs = 0
        hit = self.mod.find_native_identity_namelist(blob, identity_abs)
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit["count"], len(names))
        got = [n["name"] for n in hit["names"]]
        self.assertEqual(got, names)

    def test_canonical_prefers_full_keeps_uncovered_abbr(self) -> None:
        raw = [
            "Virgil van Dijk",
            "Mohamed Salah",
            "V. van Dijk",
            "M. Salah",
            "A. Robertson",
        ]
        canon = self.mod.canonical_ft_names(raw)
        self.assertIn("Virgil van Dijk", canon)
        self.assertIn("Mohamed Salah", canon)
        self.assertIn("A. Robertson", canon)
        self.assertNotIn("V. van Dijk", canon)
        self.assertNotIn("M. Salah", canon)

    def test_extract_mmap_native_builds_ft_players(self) -> None:
        names = [
            "Adam Smith",
            "Lewis Cook",
            "Justin Kluivert",
            "Marcus Tavernier",
            "Ryan Christie",
            "Antoine Semenyo",
            "Marcos Senesi",
            "Tyler Adams",
            "Alex Scott",
            "Amine Adli",
            "Enes Ünal",
            "Evanilson",
            "A. Smith",
            "L. Cook",
            "D. Brooks",
        ]
        ident = _identity(TAG_NATIVE, 600, "Bournemouth")
        blob = ident + bytes(510) + _namelist(names) + bytes(32)
        result = self.mod.extract_from_mmap(
            blob, save=Path("synthetic-bournemouth.fm"), t0=0.0
        )
        self.assertEqual(result["tagHex"], "00950e01")
        self.assertEqual(result["clubId"], 600)
        self.assertGreaterEqual(len(result["players"]), 12)
        player_names = [p["name"] for p in result["players"]]
        self.assertIn("Adam Smith", player_names)
        self.assertIn("D. Brooks", player_names)
        self.assertEqual(result["reserves"]["players"], [])
        self.assertEqual(result["u19"]["players"], [])
        self.assertEqual(
            result["discovery"]["unitStatus"]["FT"], "identity-namelist"
        )

    def test_continue_is_honest_not_yet(self) -> None:
        ident = _identity(TAG_CONTINUE, 742, "Schalke")
        # Even with a planted namelist, continue must not claim native lock.
        names = ["Player One", "Player Two"] + [f"P. {i}" for i in range(14)]
        blob = ident + bytes(520) + _namelist(names)
        result = self.mod.extract_from_mmap(
            blob, save=Path("synthetic-continue.fm"), t0=0.0
        )
        self.assertEqual(result["tagHex"], "00950e02")
        self.assertEqual(result["players"], [])
        self.assertEqual(
            result["discovery"]["missReason"], "continue-squad-lists-not-yet"
        )


if __name__ == "__main__":
    unittest.main()
