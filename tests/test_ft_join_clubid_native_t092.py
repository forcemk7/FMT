"""T092: FT join from identity UniqueID and native 7f02 list shape."""

from __future__ import annotations

import importlib.util
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PRE_NAME = bytes.fromhex("0091000000ffffffff9100000091000000")
LIST_SENTINEL = bytes.fromhex("7f02000000ffffffff")
LIST_SENTINEL_LOOSE = bytes.fromhex("7f02000000")
TAG_010302 = bytes.fromhex("010302")

PARENT = "Sample Town"
OTHER = "Other Place"
TEAM_ID = 1200
DUP = 3400
PERSIST = 8800
DECOY_TEAM = 1199
DECOY_DUP = 3399
CLUB_UID = 4242
DECOY_UID = 4241
JOBS_FT = [200 + i for i in range(8)]
DECOY_JOBS = [9000 + i for i in range(12)]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _lp32(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack("<I", len(raw)) + raw


def _catalog_row(name: str, team_id: int, dup: int, after: bytes = b"") -> bytes:
    return struct.pack("<III", team_id, dup, dup) + PRE_NAME + _lp32(name) + after


def _ft_body(
    team_id: int,
    dup: int,
    persist: int,
    jobs: list[int],
    *,
    sentinel: bytes = LIST_SENTINEL,
    pad_after_hdr: bytes = b"",
    zero_pad: bytes | None = None,
) -> bytes:
    mid_pad = bytes(10) if zero_pad is None else zero_pad
    body = (
        struct.pack("<I", team_id)
        + mid_pad
        + struct.pack("<I", 0x1C00)
        + struct.pack("<II", dup, dup)
        + b"\x0a"
        + pad_after_hdr
        + struct.pack("<I", persist)
        + sentinel
        + struct.pack("<H", len(jobs))
    )
    body += b"".join(struct.pack("<I", j) for j in jobs)
    return body


class FtJoinClubIdNativeT092Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ft = _load("ft_t092", ROOT / "scripts" / "ft_squad_discovery.py")

    def test_club_id_finds_list_when_short_name_is_decoy_or_absent(self) -> None:
        decoy = _catalog_row(PARENT, DECOY_TEAM, DECOY_DUP)
        live = _catalog_row(OTHER, TEAM_ID, DUP, struct.pack("<I", CLUB_UID))
        body = _ft_body(TEAM_ID, DUP, PERSIST, JOBS_FT)
        blob = decoy + (b"\x00" * 32) + live + (b"\x00" * 64) + body

        by_id = self.ft.resolve_ft_squad(blob, PARENT, club_id=CLUB_UID)
        self.assertIsNotNone(by_id)
        assert by_id is not None and by_id.get("list")
        self.assertEqual(by_id["team"]["teamId"], TEAM_ID)
        self.assertEqual(by_id["clubId"], CLUB_UID)
        self.assertEqual(by_id["list"]["jobs"], JOBS_FT)
        self.assertEqual(by_id["jobsFound"], len(JOBS_FT))

        absent = self.ft.resolve_ft_squad(blob[len(decoy) :], PARENT, club_id=CLUB_UID)
        self.assertIsNotNone(absent)
        assert absent is not None and absent.get("list")
        self.assertEqual(absent["list"]["jobs"], JOBS_FT)
        self.assertNotIn(PARENT.encode("utf-8"), blob[len(decoy) :])

        selected = self.ft.select_managed_ft_jobs(
            PARENT, by_id, fallback_jobs=DECOY_JOBS, club_id=CLUB_UID
        )
        self.assertEqual(selected["method"], "ft-club-squad-join-v1")
        self.assertEqual(selected["jobs"], JOBS_FT)

    def test_loose_7f02_and_010302_parse_without_strict_sentinel(self) -> None:
        catalog = _catalog_row(PARENT, TEAM_ID, DUP)
        loose_010302 = LIST_SENTINEL_LOOSE + TAG_010302 + b"\x00"
        body = _ft_body(
            TEAM_ID, DUP, PERSIST, JOBS_FT, sentinel=loose_010302
        )
        self.assertNotIn(LIST_SENTINEL, body)
        blob = catalog + (b"\x00" * 48) + body
        hit = self.ft.resolve_ft_squad(blob, PARENT)
        self.assertIsNotNone(hit)
        assert hit is not None and hit.get("list")
        self.assertEqual(hit["list"]["jobs"], JOBS_FT)
        self.assertEqual(hit["jobsFound"], len(JOBS_FT))

        far = _ft_body(
            TEAM_ID,
            DUP,
            PERSIST,
            JOBS_FT,
            sentinel=LIST_SENTINEL_LOOSE,
            pad_after_hdr=b"\x11" * 200,
        )
        blob_far = catalog + (b"\x00" * 48) + far
        hit_far = self.ft.resolve_ft_squad(blob_far, PARENT)
        self.assertIsNotNone(hit_far)
        assert hit_far is not None and hit_far.get("list")
        self.assertEqual(hit_far["list"]["jobs"], JOBS_FT)

        nonzero = _ft_body(
            TEAM_ID,
            DUP,
            PERSIST,
            JOBS_FT,
            zero_pad=b"\x22" * 10,
        )
        blob_nz = catalog + (b"\x00" * 48) + nonzero
        hit_nz = self.ft.resolve_ft_squad(blob_nz, PARENT)
        self.assertIsNotNone(hit_nz)
        assert hit_nz is not None and hit_nz.get("list")
        self.assertEqual(hit_nz["list"]["jobs"], JOBS_FT)

    def test_identity_known_true_miss_never_pick_tid(self) -> None:
        decoy = _catalog_row(PARENT, DECOY_TEAM, DECOY_DUP, struct.pack("<I", DECOY_UID))
        live = _catalog_row(OTHER, TEAM_ID, DUP, struct.pack("<I", CLUB_UID))
        blob = decoy + (b"\x00" * 32) + live
        hit = self.ft.resolve_ft_squad(blob, PARENT, club_id=CLUB_UID)
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertIsNone(hit.get("list"))
        self.assertEqual(hit["jobsFound"], 0)
        selected = self.ft.select_managed_ft_jobs(
            None, hit, fallback_jobs=DECOY_JOBS, club_id=CLUB_UID
        )
        self.assertEqual(selected["method"], "ft-club-squad-join-miss")
        self.assertEqual(selected["jobs"], [])
        self.assertEqual(selected["missReason"], "no-job-list")
        self.assertNotEqual(
            selected["method"], "max_manager_staff_link_among_squad_lists"
        )

    def test_progress_fields_include_jobs_found(self) -> None:
        catalog = _catalog_row(PARENT, TEAM_ID, DUP, struct.pack("<I", CLUB_UID))
        body = _ft_body(TEAM_ID, DUP, PERSIST, JOBS_FT)
        hit = self.ft.resolve_ft_squad(
            catalog + (b"\x00" * 32) + body, PARENT, club_id=CLUB_UID
        )
        selected = self.ft.select_managed_ft_jobs(
            PARENT, hit, fallback_jobs=DECOY_JOBS, club_id=CLUB_UID
        )
        fields = self.ft.ft_join_progress_fields(CLUB_UID, hit, selected)
        self.assertEqual(fields["clubId"], CLUB_UID)
        self.assertIsNone(fields["missReason"])
        self.assertGreaterEqual(fields["catalogHits"], 1)
        self.assertGreaterEqual(fields["teamObjects"], 1)
        self.assertEqual(fields["jobsFound"], len(JOBS_FT))

        miss = self.ft.resolve_ft_squad(catalog, PARENT, club_id=CLUB_UID)
        miss_sel = self.ft.select_managed_ft_jobs(
            PARENT, miss, fallback_jobs=DECOY_JOBS, club_id=CLUB_UID
        )
        miss_fields = self.ft.ft_join_progress_fields(CLUB_UID, miss, miss_sel)
        self.assertEqual(miss_fields["jobsFound"], 0)
        self.assertEqual(miss_fields["missReason"], "no-job-list")
        self.assertEqual(miss_sel["method"], "ft-club-squad-join-miss")


if __name__ == "__main__":
    unittest.main()
