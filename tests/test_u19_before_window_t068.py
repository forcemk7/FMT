"""T068: U19 live list is the before-name row even when Δ is past 220."""

from __future__ import annotations

import importlib.util
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_u19():
    spec = importlib.util.spec_from_file_location(
        "u19_t068", ROOT / "scripts" / "u19_squad_discovery.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


MOTIF = b"\xff\xff\xff\xff\x00\xff\xff\xff\xff"


def _list_blob(count: int, jobs: list[int]) -> bytes:
    body = MOTIF + struct.pack("<H", count)
    body += b"".join(struct.pack("<I", j) for j in jobs)
    return body


class U19BeforeWindowT068Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.u19 = _load_u19()

    def test_window_covers_delta_229(self) -> None:
        self.assertGreaterEqual(self.u19.LIST_WINDOW_BEFORE, 400)

    def test_before_list_at_minus_229_wins_over_after_decoy(self) -> None:
        """König 2040: live list Δ≈−229; after-name n=35 is a neighbour decoy."""
        live_jobs = [100_000 + i for i in range(18)]
        decoy_jobs = [900_000 + i for i in range(35)]
        live = _list_blob(18, live_jobs)
        decoy = _list_blob(35, decoy_jobs)
        name = "Schalke 04 U19".encode("utf-8")
        lp32 = struct.pack("<I", len(name)) + name
        # Motif → UTF-8 name start = 229 (König short-row geometry).
        prefix = 229
        pad_before = prefix - 4 - len(live)
        self.assertGreater(pad_before, 0)
        pad_after = b"\x00" * 12
        buf = live + (b"\x00" * pad_before) + lp32 + pad_after + decoy
        name_abs = buf.find(name)
        self.assertEqual(name_abs - buf.find(MOTIF), 229)

        before = self.u19.parse_list_before_name(buf, name_abs)
        after = self.u19.parse_list_after_name(buf, name_abs, len(name))
        near = self.u19.parse_list_near_name(buf, name_abs, len(name))
        self.assertIsNotNone(before)
        self.assertIsNotNone(after)
        assert before and after and near
        self.assertEqual(before["count"], 18)
        self.assertEqual(before["jobs"], live_jobs)
        self.assertEqual(after["count"], 35)
        self.assertEqual(near["jobs"], live_jobs)
        self.assertEqual(near["delta"], before["delta"])

    def test_old_delta_165_still_hits(self) -> None:
        jobs = [200_000 + i for i in range(25)]
        live = _list_blob(25, jobs)
        name = "Schalke 04 U19".encode("utf-8")
        lp32 = struct.pack("<I", len(name)) + name
        pad = b"\x00" * (165 - len(live))
        buf = live + pad + lp32
        name_abs = buf.find(name)
        hit = self.u19.parse_list_before_name(buf, name_abs)
        self.assertIsNotNone(hit)
        assert hit
        self.assertEqual(hit["jobs"], jobs)


if __name__ == "__main__":
    unittest.main()
