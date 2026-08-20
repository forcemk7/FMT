"""T118: At-club Senior UniqueIDs from club .dat — mentoring pool (not +488)."""

from __future__ import annotations

import importlib.util
import json
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "data" / "saves" / "gameDate8.fm"
GOLD_PATH = ROOT / "tests" / "fixtures" / "t115-santos-gold.json"
TAG_NATIVE = bytes.fromhex("00950e01")
TAG_CONTINUE = bytes.fromhex("00950e02")
TAD = b"tad."
PERSON_02_40 = bytes.fromhex("0240")
LOAN_OUT_PAD = b"\x00\x00\x00\x00\xff\xff\xff\xff\xff\x00\x00\x00\x00"


def _load():
    spec = importlib.util.spec_from_file_location(
        "esl_t118", ROOT / "scripts" / "extract-squad-lists.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _lp32(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack("<I", len(raw)) + raw


def _identity(tag: bytes, club: str, uid: int) -> bytes:
    return tag + _lp32("Pat Example") + _lp32(club) + struct.pack("<I", uid)


def _person(kind: int, sub: int, intern: int, uid: int) -> bytes:
    return (
        b"\x00" * 5
        + bytes((0x02, 0x40, kind, sub, 0, 0, 0))
        + struct.pack("<I", intern)
        + struct.pack("<II", uid, uid)
        + b"\x00" * 32
    )


def _club_dat(club_id: int, interns: list[int]) -> bytes:
    return (
        TAD
        + b"\x00" * 64
        + struct.pack("<I", club_id)
        + b"\x00" * 32
        + struct.pack("<I", len(interns))
        + b"".join(struct.pack("<I", i) for i in interns)
        + b"\x00" * 16
    )


def _loan_template(*, intern: int, loan_club: int) -> bytes:
    """Minimal loan-out template with intern in lookback."""
    # lookback distance 40
    body = struct.pack("<I", intern) + b"\x00" * 36
    body += LOAN_OUT_PAD
    body += b"\x64\xff\x24"
    body += b"\x00" * 4  # after kind
    body += b"\x00" * 10
    body += b"\x00" * 4
    body += struct.pack("<II", loan_club, loan_club)
    body += struct.pack("<H", 0x000A)
    return body


class AtClubSeniorMentoringPoolT118Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load()
        cls.gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))

    def test_method_is_club_dat_not_plus488(self) -> None:
        src = (ROOT / "scripts" / "extract-squad-lists.py").read_text(encoding="utf-8")
        self.assertIn("native-club-dat-senior-v1", src)
        self.assertNotIn("native-clubid-plus488-v1", src)
        self.assertNotIn("CLUB_ID_NAMELIST_REL = 488", src)
        self.assertNotIn("2000206937", src)
        self.assertNotIn("19383039", src)
        self.assertTrue(GOLD_PATH.is_file())
        self.assertNotIn("19333767", src)

    def test_synthetic_drops_loaned_out_intern(self) -> None:
        club_id = 335
        # 8 at-club + 1 outbound (intern 8096 / Moisés-class)
        people = [(1000 + i, 19000000 + i) for i in range(8)]
        people[0] = (3727, 19024412)
        people[1] = (5356, 19215476)
        people[7] = (8096, 19383039)
        blob = _identity(TAG_NATIVE, "Santos", club_id)
        for intern, uid in people:
            blob += _person(0x10, 0x04, intern, uid)
        blob += _club_dat(club_id, [p[0] for p in people])
        blob += _loan_template(intern=8096, loan_club=14022190)
        result = self.mod.extract_from_mmap(blob, save=Path("synthetic-t118.fm"), t0=0.0)
        uids = {p["uid"] for p in result["players"]}
        self.assertNotIn(19383039, uids)
        self.assertIn(19024412, uids)
        self.assertIn(19215476, uids)
        self.assertEqual(result["discovery"]["method"], "native-club-dat-senior-v1")
        self.assertEqual(result["players"][0]["_extract"]["unit"], "senior")
        self.assertTrue(result["players"][0]["_extract"]["uidResolved"])
        self.assertEqual(len(result["discovery"]["loanedOutDropped"]), 1)
        self.assertEqual(result["discovery"]["loanedOutDropped"][0]["uid"], 19383039)

    def test_continue_skips_club_dat(self) -> None:
        club_id = 790
        people = [(1000 + i, 19000000 + i) for i in range(8)]
        blob = _identity(TAG_CONTINUE, "FC Schalke 04", club_id)
        for intern, uid in people:
            blob += _person(0x10, 0x04, intern, uid)
        blob += _club_dat(club_id, [p[0] for p in people])
        result = self.mod.extract_from_mmap(blob, save=Path("synthetic-cont.fm"), t0=0.0)
        self.assertEqual(result["players"], [])
        self.assertEqual(
            result["discovery"]["missReason"],
            "continue-skip-native-club-dat",
        )

    @unittest.skipUnless(SAVE.is_file(), "data/saves/gameDate8.fm missing")
    def test_gameDate8_at_club_senior_vs_gold(self) -> None:
        import mmap
        import shutil
        import tempfile

        work_dir = ROOT / "tmp" / "t118-work"
        work_dir.mkdir(parents=True, exist_ok=True)
        work = work_dir / SAVE.name
        shutil.copy2(SAVE, work)
        tmp = None
        try:
            self.mod.refuse_live_fm_games_save(work)
            tmp = self.mod.decompress_to_temp(work, 0.0)
            with tmp.open("rb") as f:
                mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                try:
                    result = self.mod.extract_from_mmap(mm, save=work, t0=0.0)
                finally:
                    mm.close()
        finally:
            if tmp is not None:
                tmp.unlink(missing_ok=True)
            work.unlink(missing_ok=True)

        white = {int(x) for x in self.gold["owned_at_club"]}
        inbound = {int(x) for x in self.gold["inbound_loan"]}
        outbound = {int(x) for x in self.gold["owned_out_on_loan"]}
        at_club = white | inbound
        got = {int(p["uid"]) for p in result["players"]}

        self.assertEqual(result["clubId"], 335)
        self.assertEqual(result["discovery"]["method"], "native-club-dat-senior-v1")
        self.assertTrue(all(p["_extract"]["uidResolved"] for p in result["players"]))
        self.assertTrue(all(p["_extract"]["unit"] == "senior" for p in result["players"]))
        # Owned-out absent (Moisés must be dropped).
        self.assertEqual(got & outbound, set())
        # At-club present.
        missing = at_club - got
        self.assertEqual(missing, set(), msg=f"missing at-club UniqueIDs: {missing}")
        self.assertEqual(got - at_club, set(), msg=f"unexpected UIDs: {got - at_club}")
        self.assertEqual(len(got), 31)
        # Names are real strings, not uid: fallback for gold set.
        for p in result["players"]:
            self.assertFalse(
                str(p["name"]).startswith("uid:"),
                msg=f"uid={p['uid']} name={p['name']!r}",
            )


if __name__ == "__main__":
    unittest.main()
