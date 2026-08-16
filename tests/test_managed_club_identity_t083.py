"""T083: managed-club identity parser on a synthetic blob — not a Career Save."""

from __future__ import annotations

import importlib.util
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TAG_01 = bytes.fromhex("00950e01")
TAG_02 = bytes.fromhex("00950e02")
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


def _identity_blob(tag: bytes, person: str, club: str, uid: int) -> bytes:
    return tag + _lp32(person) + _lp32(club) + struct.pack("<I", uid)


class ManagedClubIdentityT083Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.emt = _load("emt_t083", ROOT / "scripts" / "extract-managed-team.py")
        cls.eft = _load("eft_t083", ROOT / "scripts" / "extract-first-team-fast.py")

    def test_tag_01_person_club_uid(self) -> None:
        blob = _identity_blob(TAG_01, PERSON, CLUB, CLUB_UID)
        hit = self.emt.discover_managed_club(blob, len(blob))
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit["managerName"], PERSON)
        self.assertEqual(hit["clubNameShort"], CLUB)
        self.assertEqual(hit["clubId"], CLUB_UID)
        self.assertEqual(hit["tagHex"], TAG_01.hex())
        self.assertEqual(hit["method"], "human_tag_club_uid")

    def test_tag_02_person_club_uid(self) -> None:
        blob = _identity_blob(TAG_02, PERSON, CLUB, CLUB_UID)
        hit = self.emt.discover_managed_club(blob, len(blob))
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit["managerName"], PERSON)
        self.assertEqual(hit["clubNameShort"], CLUB)
        self.assertEqual(hit["clubId"], CLUB_UID)
        self.assertEqual(hit["tagHex"], TAG_02.hex())

    def test_first_team_extract_uses_same_parser(self) -> None:
        blob = _identity_blob(TAG_01, PERSON, CLUB, CLUB_UID)
        a = self.emt.discover_managed_club(blob, len(blob))
        b = self.eft.discover_managed_club(blob, len(blob))
        self.assertEqual(a, b)
        self.assertEqual(a["clubId"], CLUB_UID)

    def test_deadline_is_a_bound_not_fail_when_tag_sits_later(self) -> None:
        pad = self.emt.IDENTITY_DEADLINE + 64
        blob = b"\xaa" * pad + _identity_blob(TAG_02, PERSON, CLUB, CLUB_UID)
        self.assertIsNone(self.emt.discover_managed_club(blob, self.emt.EARLY_SCAN))
        self.assertIsNone(self.emt.discover_managed_club(blob, self.emt.IDENTITY_DEADLINE))
        hit, diag = self.emt.try_discover_managed_club(
            blob,
            limits=(
                self.emt.EARLY_SCAN,
                self.emt.IDENTITY_DEADLINE,
                len(blob),
            ),
        )
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit["clubId"], CLUB_UID)
        self.assertEqual(hit["clubNameShort"], CLUB)
        self.assertTrue(diag["identityFound"])
        self.assertGreater(diag["searchBound"], self.emt.IDENTITY_DEADLINE)
        self.assertEqual(diag["bytesScanned"], diag["searchBound"])

    def test_miss_is_diagnostic_not_a_club(self) -> None:
        blob = b"\x00" * 256 + TAG_01 + b"\x00\x00\x00\x00"
        hit, diag = self.emt.try_discover_managed_club(blob)
        self.assertIsNone(hit)
        self.assertFalse(diag["identityFound"])
        self.assertEqual(diag["bytesScanned"], len(blob))
        self.assertEqual(diag["tagHexes"], [TAG_01.hex(), TAG_02.hex()])
        self.assertGreaterEqual(diag["tags"][TAG_01.hex()]["count"], 1)
        self.assertIsInstance(diag["lastTagAbs"], int)
        self.assertNotIn("clubId", diag)
        self.assertNotIn("clubNameShort", diag)

    def test_garbage_after_tag_does_not_invent_a_club(self) -> None:
        decoy = TAG_01 + struct.pack("<I", 4) + b"\x01\x02\x03\x04"
        later = _identity_blob(TAG_01, PERSON, CLUB, CLUB_UID)
        blob = decoy + b"\x00" * 32 + later
        hit = self.emt.discover_managed_club(blob, len(blob))
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit["clubId"], CLUB_UID)
        self.assertEqual(hit["clubNameShort"], CLUB)


if __name__ == "__main__":
    unittest.main()
