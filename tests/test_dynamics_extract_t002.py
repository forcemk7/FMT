"""T002: FT extract fills captaincy + social group + list-order rank vs screenshot GT."""

from __future__ import annotations

import importlib.util
import json
import mmap
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN_A = ROOT / "tmp" / "fm-spike" / "t001-a.bin"
BIN_B = ROOT / "tmp" / "fm-spike" / "t001-b.bin"
GT_A = ROOT / "data" / "fixtures" / "dynamics-ground-truth-baseline-wip.json"
GT_B = ROOT / "data" / "fixtures" / "dynamics-ground-truth-post-captaincy-wip.json"
TID = 193616


def _load_eft():
    spec = importlib.util.spec_from_file_location(
        "eft_t002", ROOT / "scripts" / "extract-first-team-fast.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _extract_on(mod, mm) -> tuple[list[int], list[dict]]:
    list_abs, _count, jobs = mod.discover_squads(mm)[TID]
    players = [{"jobId": job} for job in jobs]
    mod.apply_ft_dynamics(mm, players, list_abs, jobs)
    return jobs, players


def _assert_gt_membership(test: unittest.TestCase, players: list[dict], gt: dict) -> None:
    by_job = {int(p["jobId"]): p["dynamics"] for p in players}
    cap_name = gt["summary"]["captaincy"]["captain"]
    vc_name = gt["summary"]["captaincy"]["viceCaptain"]
    name_job = {row["name"]: int(row["jobId"]) for row in gt["players"]}

    cap_dyn = by_job[name_job[cap_name]]
    vc_dyn = by_job[name_job[vc_name]]
    test.assertEqual(cap_dyn["captaincy"], "captain")
    test.assertEqual(vc_dyn["captaincy"], "viceCaptain")

    for row in gt["players"]:
        job = int(row["jobId"])
        test.assertIn(job, by_job)
        dyn = by_job[job]
        test.assertIsNone(dyn["hierarchy"], row["name"])
        test.assertEqual(dyn["socialGroup"], row["socialGroup"], row["name"])
        if row.get("captaincy"):
            test.assertEqual(dyn["captaincy"], row["captaincy"], row["name"])
        else:
            test.assertIsNone(dyn["captaincy"], row["name"])

    for label in ("core", "secondaryA", "other"):
        gt_order = [int(p["jobId"]) for p in gt["players"] if p["socialGroup"] == label]
        ranks = [by_job[job]["socialRank"] for job in gt_order]
        test.assertEqual(ranks, list(range(len(gt_order))), label)

    for dyn in by_job.values():
        test.assertIsNone(dyn["hierarchy"])
        test.assertNotIn(dyn.get("hierarchy"), ("teamLeader", "highlyInfluential"))


class TestDynamicsExtractSynthetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.eft = _load_eft()

    def test_motif_missing_leaves_social_null_and_does_not_crash(self) -> None:
        jobs = [100001, 100002, 100003]
        cap, vc, pad, mask = jobs[0], jobs[1], 0, 0xFFFFFFFF
        buf = struct.pack("<IIIIIII", *jobs, cap, vc, pad, mask)
        players = [{"jobId": job} for job in jobs]
        self.eft.apply_ft_dynamics(buf, players, 0, jobs)
        for player in players:
            dyn = player["dynamics"]
            self.assertIsNone(dyn["socialGroup"])
            self.assertIsNone(dyn["socialRank"])
            self.assertIsNone(dyn["hierarchy"])
        self.assertEqual(players[0]["dynamics"]["captaincy"], "captain")
        self.assertEqual(players[1]["dynamics"]["captaincy"], "viceCaptain")
        self.assertIsNone(players[2]["dynamics"]["captaincy"])

    def test_motif_lists_fill_group_and_rank(self) -> None:
        jobs = [100001, 100002, 100003]
        list_abs = 0
        body = struct.pack("<IIIIIII", *jobs, jobs[2], jobs[0], 0, 0xFFFFFFFF)
        motif = self.eft.DYNAMICS_SOCIAL_MOTIF
        social = (
            struct.pack("<HII", 2, jobs[0], jobs[1])  # core
            + struct.pack("<HI", 1, jobs[2])  # secondaryA
            + struct.pack("<H", 0)  # secondaryB
            + struct.pack("<H", 0)  # other
        )
        buf = body + motif + social
        players = [{"jobId": job} for job in jobs]
        self.eft.apply_ft_dynamics(buf, players, list_abs, jobs)
        by_job = {p["jobId"]: p["dynamics"] for p in players}
        self.assertEqual(by_job[100001]["socialGroup"], "core")
        self.assertEqual(by_job[100001]["socialRank"], 0)
        self.assertEqual(by_job[100002]["socialGroup"], "core")
        self.assertEqual(by_job[100002]["socialRank"], 1)
        self.assertEqual(by_job[100003]["socialGroup"], "secondaryA")
        self.assertEqual(by_job[100003]["socialRank"], 0)
        self.assertEqual(by_job[100003]["captaincy"], "captain")
        self.assertEqual(by_job[100001]["captaincy"], "viceCaptain")
        self.assertIsNone(by_job[100001]["hierarchy"])


@unittest.skipUnless(
    BIN_A.is_file() and BIN_B.is_file() and GT_A.is_file() and GT_B.is_file(),
    "dynamics A/B bins or screenshot GT missing",
)
class TestDynamicsExtractGt(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.eft = _load_eft()
        cls.gt_a = _read_json(GT_A)
        cls.gt_b = _read_json(GT_B)

    def test_save_a_matches_screenshot_membership(self) -> None:
        with BIN_A.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                _jobs, players = _extract_on(self.eft, mm)
            finally:
                mm.close()
        _assert_gt_membership(self, players, self.gt_a)

    def test_save_b_matches_screenshot_membership(self) -> None:
        with BIN_B.open("rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                _jobs, players = _extract_on(self.eft, mm)
            finally:
                mm.close()
        _assert_gt_membership(self, players, self.gt_b)
        cap_job = next(
            int(p["jobId"])
            for p in self.gt_b["players"]
            if p["name"] == self.gt_b["summary"]["captaincy"]["captain"]
        )
        a_cap_job = next(
            int(p["jobId"])
            for p in self.gt_a["players"]
            if p["name"] == self.gt_a["summary"]["captaincy"]["captain"]
        )
        self.assertNotEqual(cap_job, a_cap_job)
