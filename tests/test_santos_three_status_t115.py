"""T115: Santos UniqueID lock — club .dat intern list + gold person doubles."""

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


def _load():
    spec = importlib.util.spec_from_file_location(
        "t115_lock", ROOT / "scripts" / "lock-santos-three-status.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _lp32(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack("<I", len(raw)) + raw


def _identity(club: str, uid: int) -> bytes:
    return TAG_NATIVE + _lp32("Pat Example") + _lp32(club) + struct.pack("<I", uid)


def _person(kind: int, sub: int, intern: int, uid: int) -> bytes:
    return (
        b"\x00" * 5
        + bytes((0x02, 0x40, kind, sub, 0, 0, 0))
        + struct.pack("<I", intern)
        + struct.pack("<II", uid, uid)
        + b"\x00" * 32
    )


def _club_dat(club_id: int, interns: list[int]) -> bytes:
    body = (
        b"tad."
        + b"\x00" * 64
        + struct.pack("<I", club_id)
        + b"\x00" * 32
        + struct.pack("<I", len(interns))
        + b"".join(struct.pack("<I", i) for i in interns)
        + b"\x00" * 16
    )
    return body


class SantosThreeStatusT115Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load()
        cls.gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))

    def test_gold_lives_in_fixtures_not_extract(self) -> None:
        extract = (ROOT / "scripts" / "extract-squad-lists.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("2000206937", extract)
        self.assertNotIn("19333767", extract)
        src = (ROOT / "scripts" / "lock-santos-three-status.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("t115-santos-gold.json", src)
        self.assertIn("fixtures", src)
        self.assertNotIn("CLUB_ID_NAMELIST_REL = 488", src)
        self.assertEqual(len(self.gold["owned_at_club"]), 28)
        self.assertEqual(len(self.gold["owned_out_on_loan"]), 11)
        self.assertEqual(len(self.gold["inbound_loan"]), 3)

    def test_synthetic_club_dat_intern_list(self) -> None:
        club_id = 335
        people = [
            (3727 + i, 19024412 + i) for i in range(8)
        ]
        people[0] = (3727, 19024412)
        people[1] = (5356, 19215476)
        people[2] = (7083, 19333767)
        blob = _identity("Santos", club_id)
        for intern, uid in people:
            blob += _person(0x10, 0x04, intern, uid)
        blob += _club_dat(club_id, [p[0] for p in people])
        persons = self.mod.scan_person_doubles(blob)
        self.assertEqual(len(persons), 8)
        self.assertEqual(persons[3727]["uid"], 19024412)
        parsed = self.mod.find_club_dat_intern_list(blob, club_id, persons)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["count"], 8)
        self.assertEqual(parsed["players"][0]["uid"], 19024412)
        self.assertEqual(parsed["players"][1]["uid"], 19215476)
        self.assertEqual(parsed["players"][2]["uid"], 19333767)

    def test_synthetic_identity_then_lock(self) -> None:
        club_id = 335
        people = [(1000 + i, 19000000 + i) for i in range(8)]
        people[0] = (3727, 19024412)
        people[1] = (5356, 19215476)
        people[2] = (8096, 19383039)
        blob = _identity("Santos", club_id)
        for intern, uid in people:
            blob += _person(0x10, 0x04, intern, uid)
        blob += _club_dat(club_id, [p[0] for p in people])
        gold = {
            "owned_at_club": {"19024412": "Neymar", "19215476": "Luan Peres"},
            "owned_out_on_loan": {"19383039": "Moisés"},
            "inbound_loan": {},
        }
        result = self.mod.lock_from_mmap(blob, gold=gold)
        self.assertEqual(result["clubId"], club_id)
        self.assertEqual(result["clubSeniorList"]["count"], 8)
        self.assertEqual(len(result["goldFound"]), 3)
        self.assertEqual(
            result["vsGold"]["inClubSeniorList"]["owned_out_on_loan"],
            [19383039],
        )

    @unittest.skipUnless(SAVE.is_file(), "data/saves/gameDate8.fm missing")
    def test_gameDate8_person_doubles_and_club_list(self) -> None:
        work = self.mod.working_copy(SAVE)
        tmp = None
        try:
            tmp = self.mod.decompress_to_temp(work)
            with tmp.open("rb") as f:
                import mmap

                mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                try:
                    result = self.mod.lock_from_mmap(mm, gold=self.gold)
                finally:
                    mm.close()
        finally:
            if tmp is not None:
                tmp.unlink(missing_ok=True)
            work.unlink(missing_ok=True)

        all_gold = (
            set(int(x) for x in self.gold["owned_at_club"])
            | set(int(x) for x in self.gold["owned_out_on_loan"])
            | set(int(x) for x in self.gold["inbound_loan"])
        )
        found = {row["uid"] for row in result["goldFound"]}
        self.assertEqual(found, all_gold)
        self.assertEqual(result["goldMissingPersonDouble"], [])
        self.assertEqual(result["clubSeniorList"]["count"], 32)
        list_uids = {row["uid"] for row in result["clubSeniorList"]["players"]}
        whites = {int(x) for x in self.gold["owned_at_club"]}
        inbound = {int(x) for x in self.gold["inbound_loan"]}
        outbound = {int(x) for x in self.gold["owned_out_on_loan"]}
        self.assertEqual(whites & list_uids, whites)
        self.assertEqual(inbound & list_uids, inbound)
        self.assertEqual(outbound & list_uids, {19383039})
        missing_out = set(result["blocked"]["ownedOutMissingFromClubList"])
        self.assertEqual(missing_out, outbound - {19383039})
        self.assertEqual(len(missing_out), 10)


if __name__ == "__main__":
    unittest.main()
