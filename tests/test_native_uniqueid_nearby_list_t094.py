"""T094: native UniqueID then nearby 7f02+010302 (padding between; glued still hits)."""

from __future__ import annotations

import importlib.util
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LIST_SENTINEL = bytes.fromhex("7f02000000ffffffff")
LIST_SENTINEL_LOOSE = bytes.fromhex("7f02000000")
TAG_010302 = bytes.fromhex("010302")
TAG_NATIVE = bytes.fromhex("00950e01")
TAG_CONTINUE = bytes.fromhex("00950e02")
PRE_NAME = bytes.fromhex("0091000000ffffffff9100000091000000")

PERSON = "Pat Example"
PARENT = "Sample Town"
TEAM_ID = 1200
DUP = 3400
PERSIST = 8800
CLUB_UID = 4242
DECOY_UID = 4241
JOBS_FT = [200 + i for i in range(8)]
DECOY_JOBS = [9000 + i for i in range(12)]
# Synthetic gap only — larger than first LIST_WINDOWS entry, not a save offset.
PAD_BETWEEN = 200


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _lp32(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack("<I", len(raw)) + raw


def _identity(tag: bytes, uid: int, club: str = PARENT) -> bytes:
    return tag + _lp32(PERSON) + _lp32(club) + struct.pack("<I", uid)


def _catalog_row(name: str, team_id: int, dup: int, after: bytes = b"") -> bytes:
    return struct.pack("<III", team_id, dup, dup) + PRE_NAME + _lp32(name) + after


def _ft_body(
    team_id: int,
    dup: int,
    persist: int,
    jobs: list[int],
    *,
    sentinel: bytes = LIST_SENTINEL,
) -> bytes:
    body = (
        struct.pack("<I", team_id)
        + bytes(10)
        + struct.pack("<I", 0x1C00)
        + struct.pack("<II", dup, dup)
        + b"\x0a"
        + struct.pack("<I", persist)
        + sentinel
        + struct.pack("<H", len(jobs))
    )
    body += b"".join(struct.pack("<I", j) for j in jobs)
    return body


def _native_list_glued(club_id: int, jobs: list[int]) -> bytes:
    return (
        struct.pack("<I", club_id)
        + LIST_SENTINEL_LOOSE
        + TAG_010302
        + b"\x00"
        + struct.pack("<H", len(jobs))
        + b"".join(struct.pack("<I", j) for j in jobs)
    )


def _native_list_padded(club_id: int, jobs: list[int], pad: bytes) -> bytes:
    return (
        struct.pack("<I", club_id)
        + pad
        + LIST_SENTINEL_LOOSE
        + TAG_010302
        + b"\x00"
        + struct.pack("<H", len(jobs))
        + b"".join(struct.pack("<I", j) for j in jobs)
    )


class NativeUniqueIdNearbyListT094Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.eft = _load("eft_t094", ROOT / "scripts" / "extract-first-team-fast.py")
        cls.ft = _load("ft_t094", ROOT / "scripts" / "ft_squad_discovery.py")
        cls.emt = _load("emt_t094", ROOT / "scripts" / "extract-managed-team.py")

    def _resolve_native(self, blob: bytes):
        hit = self.emt.discover_managed_club(blob, len(blob))
        self.assertIsNotNone(hit)
        assert hit is not None
        layout = self.eft.classify_squad_layout(tag_hex=hit["tagHex"])
        self.assertEqual(layout, "native")
        ft_hit = self.eft.resolve_managed_ft_for_layout(
            blob, hit["clubNameShort"], hit["clubId"], layout=layout
        )
        return hit, layout, ft_hit

    def test_padded_uniqueid_then_010302_yields_ft_jobs(self) -> None:
        ident = _identity(TAG_NATIVE, CLUB_UID)
        decoy = _native_list_glued(DECOY_UID, DECOY_JOBS)
        pad = bytes(PAD_BETWEEN)
        live = _native_list_padded(CLUB_UID, JOBS_FT, pad)
        self.assertGreater(PAD_BETWEEN, self.eft.LIST_WINDOWS[0])
        self.assertLess(PAD_BETWEEN, self.eft.LIST_WINDOWS[1])
        self.assertNotIn(struct.pack("<I", CLUB_UID) + LIST_SENTINEL_LOOSE, live)
        blob = decoy + (b"\x00" * 32) + ident + (b"\x00" * 16) + live
        self.assertNotIn(LIST_SENTINEL, blob)

        hit, layout, ft_hit = self._resolve_native(blob)
        self.assertIsNotNone(ft_hit)
        assert ft_hit is not None and ft_hit.get("list")
        self.assertEqual(ft_hit["list"]["jobs"], JOBS_FT)
        self.assertIn("010302", ft_hit["list"]["listLayout"])
        self.assertGreater(ft_hit["list"]["sentinelAbs"] - 4, 0)

        selected = self.ft.select_managed_ft_jobs(
            hit["clubNameShort"],
            ft_hit,
            fallback_jobs=DECOY_JOBS,
            club_id=hit["clubId"],
        )
        self.assertEqual(selected["method"], "ft-club-squad-join-v1")
        self.assertEqual(selected["jobs"], JOBS_FT)

        fields = self.ft.ft_join_progress_fields(
            hit["clubId"], ft_hit, selected, layout=layout
        )
        self.assertEqual(fields["layout"], "native")
        self.assertEqual(fields["jobsFound"], len(JOBS_FT))
        self.assertIsNone(fields["missReason"])

    def test_glued_uniqueid_7f02_still_hits(self) -> None:
        ident = _identity(TAG_NATIVE, CLUB_UID)
        live = _native_list_glued(CLUB_UID, JOBS_FT)
        blob = ident + (b"\x00" * 48) + live
        _hit, _layout, ft_hit = self._resolve_native(blob)
        self.assertIsNotNone(ft_hit)
        assert ft_hit is not None and ft_hit.get("list")
        self.assertEqual(ft_hit["list"]["jobs"], JOBS_FT)

    def test_continue_blob_7f02_ffffffff_still_yields_ft_jobs(self) -> None:
        ident = _identity(TAG_CONTINUE, CLUB_UID)
        catalog = _catalog_row(PARENT, TEAM_ID, DUP, struct.pack("<I", CLUB_UID))
        body = _ft_body(TEAM_ID, DUP, PERSIST, JOBS_FT)
        decoy_native = _native_list_glued(DECOY_UID, DECOY_JOBS)
        blob = ident + (b"\x00" * 32) + catalog + (b"\x00" * 64) + body + decoy_native

        hit = self.emt.discover_managed_club(blob, len(blob))
        self.assertIsNotNone(hit)
        assert hit is not None
        layout = self.eft.classify_squad_layout(tag_hex=hit["tagHex"])
        self.assertEqual(layout, "continue")
        ft_hit = self.eft.resolve_managed_ft_for_layout(
            blob, hit["clubNameShort"], hit["clubId"], layout=layout
        )
        self.assertIsNotNone(ft_hit)
        assert ft_hit is not None and ft_hit.get("list")
        self.assertEqual(ft_hit["list"]["jobs"], JOBS_FT)
        self.assertEqual(ft_hit["team"]["teamId"], TEAM_ID)

        selected = self.ft.select_managed_ft_jobs(
            hit["clubNameShort"],
            ft_hit,
            fallback_jobs=DECOY_JOBS,
            club_id=hit["clubId"],
        )
        self.assertEqual(selected["method"], "ft-club-squad-join-v1")
        self.assertEqual(selected["jobs"], JOBS_FT)
        fields = self.ft.ft_join_progress_fields(
            hit["clubId"], ft_hit, selected, layout=layout
        )
        self.assertEqual(fields["layout"], "continue")
        self.assertEqual(fields["jobsFound"], len(JOBS_FT))

    def test_native_identity_known_miss_never_pick_tid(self) -> None:
        ident = _identity(TAG_NATIVE, CLUB_UID)
        decoy = _native_list_glued(DECOY_UID, DECOY_JOBS)
        far = (
            LIST_SENTINEL_LOOSE
            + TAG_010302
            + b"\x00"
            + struct.pack("<H", len(JOBS_FT))
            + b"".join(struct.pack("<I", j) for j in JOBS_FT)
        )
        # Other club's glued list is behind UniqueID (forward miss). A 7f02
        # past the last expand window is not a world walk.
        gap = self.eft.LIST_WINDOWS[-1] + 64
        blob = decoy + ident + (b"\x00" * gap) + far
        hit, layout, ft_hit = self._resolve_native(blob)
        self.assertIsNotNone(ft_hit)
        assert ft_hit is not None
        self.assertIsNone(ft_hit.get("list"))
        self.assertEqual(ft_hit["jobsFound"], 0)

        selected = self.ft.select_managed_ft_jobs(
            hit["clubNameShort"],
            ft_hit,
            fallback_jobs=DECOY_JOBS,
            club_id=hit["clubId"],
        )
        self.assertEqual(selected["method"], "ft-club-squad-join-miss")
        self.assertEqual(selected["jobs"], [])
        self.assertNotEqual(
            selected["method"], "max_manager_staff_link_among_squad_lists"
        )
        fields = self.ft.ft_join_progress_fields(
            hit["clubId"], ft_hit, selected, layout=layout
        )
        self.assertEqual(fields["layout"], "native")
        self.assertEqual(fields["jobsFound"], 0)
        self.assertTrue(fields["missReason"])


if __name__ == "__main__":
    unittest.main()
