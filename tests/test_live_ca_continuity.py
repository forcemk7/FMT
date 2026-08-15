#!/usr/bin/env python3
"""Unit tests for CA live-card continuity (no .fm required)."""

from __future__ import annotations

import importlib.util
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "extract_ft", ROOT / "scripts" / "extract-first-team-fast.py"
)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def _synth_attr_card(
    *,
    mental: list[int],
    physical: list[int] | None = None,
    tech: int = 70,
    u16: int = 100,
    b23: int = 20,
) -> bytes:
    """Minimal 69-byte buffer that passes is_attrish + decode_attrs."""
    assert len(mental) == 14
    rec = bytearray(69)
    for i, v in enumerate(mental):
        rec[i] = v * 5
    phys = physical or [10] * 8
    assert len(phys) == 8
    for i, v in enumerate(phys):
        rec[14 + i] = v * 5
    rec[22] = 1
    rec[23] = b23
    rec[24] = 1
    # zeros at 34/35 + seal at 43 == 0x01 (is_attrish)
    rec[43] = 0x01
    struct.pack_into("<H", rec, 36, u16)
    for i in range(55, 69):
        rec[i] = tech
    return bytes(rec)


# Outfield mental layout: aggression…concentration (Det=index 5, Lea=index 7).
TIP_MENTAL = [10, 11, 12, 10, 13, 14, 9, 6, 12, 11, 14, 12, 13, 12]
# Foreign decoy — high Det / tiny Lea plus scattered mental/phys noise (L1>>80).
DECOY_MENTAL = [1, 2, 3, 4, 5, 20, 1, 2, 1, 2, 3, 1, 2, 1]
DECOY_PHYS = [1, 2, 1, 2, 1, 2, 1, 2]


class LiveCardContinuityTests(unittest.TestCase):
    def test_ensure_live_rejects_large_l1_and_reports_status(self):
        tip = mod._ca_point_from_rec(
            _synth_attr_card(mental=TIP_MENTAL, u16=200)
        )
        assert tip is not None
        history = [tip]
        # tech=0 → wiped; mental/phys L1 to tip >>80 → unrecovered → rejected
        live = _synth_attr_card(
            mental=DECOY_MENTAL, physical=DECOY_PHYS, tech=0, u16=0, b23=40
        )
        out, status = mod.ensure_live_ca_on_history(history, live, gap=3000)
        self.assertEqual(status, "rejected")
        self.assertEqual(len(out or []), 1)
        self.assertEqual(out[-1]["mental"]["determination"], 14)

    def test_hist0_wiped_decoy_rejected_not_seeded(self):
        """T014: Gilson-class — wiped Det20 lookback must not become hist tip."""
        decoy = _synth_attr_card(
            mental=DECOY_MENTAL, physical=DECOY_PHYS, tech=0, u16=0, b23=83
        )
        out, status = mod.ensure_live_ca_on_history(None, decoy, gap=11107)
        self.assertEqual(status, "rejected")
        self.assertFalse(out)

    def test_rejected_without_tip_must_not_use_decoded_det_lea(self):
        """T014: extract must leave Det/Lea null when decoy rejected and hist=0."""
        decoy = _synth_attr_card(
            mental=DECOY_MENTAL, physical=DECOY_PHYS, tech=0, u16=0, b23=83
        )
        decoded = mod.decode_attrs(decoy)
        self.assertEqual(decoded["mental"]["determination"], 20)
        self.assertEqual(decoded["mental"]["leadership"], 2)
        history, status = mod.ensure_live_ca_on_history(None, decoy, gap=3000)
        self.assertEqual(status, "rejected")
        # Mirror extract-first-team-fast resolve: rejected + no tip → nulls
        tip = history[-1] if history else None
        if status == "rejected" and tip is None:
            det = lea = None
        else:
            det = decoded["mental"]["determination"]
            lea = decoded["mental"]["leadership"]
        self.assertIsNone(det)
        self.assertIsNone(lea)

    def test_first_wiped_progress_tip_keeps_det_lea(self):
        """T014: Gilson first tip — tech wiped, u16>0, in-band gap → Det/Lea live."""
        gilson_mental = [14, 19, 17, 15, 17, 14, 12, 16, 12, 16, 15, 13, 14, 18]
        card = _synth_attr_card(
            mental=gilson_mental, tech=0, u16=41360, b23=40
        )
        # Foreign decoy shape still rejected (u16=0).
        decoy = _synth_attr_card(
            mental=DECOY_MENTAL, physical=DECOY_PHYS, tech=0, u16=0, b23=83
        )
        self.assertIsNone(mod._ca_point_from_rec(decoy, gap=2060))

        point = mod._ca_point_from_rec(card, gap=2060)
        assert point is not None
        self.assertEqual(point["mental"]["determination"], 14)
        self.assertEqual(point["mental"]["leadership"], 16)
        self.assertNotIn("technical", point)

        # Out-of-band gap must not unlock hist=0 wiped cards.
        self.assertIsNone(mod._ca_point_from_rec(card, gap=30_000))

        history = mod.build_ca_history(card + bytes([0x11] * 2_500))
        self.assertEqual(len(history), 1)
        self.assertEqual(history[-1]["mental"]["determination"], 14)
        self.assertEqual(history[-1]["mental"]["leadership"], 16)

        out, status = mod.ensure_live_ca_on_history(None, card, gap=2060)
        self.assertEqual(status, "appended")
        self.assertEqual(out[-1]["mental"]["determination"], 14)
        self.assertEqual(out[-1]["mental"]["leadership"], 16)

        # Live same tip → same (tech stripped on both sides).
        out2, status2 = mod.ensure_live_ca_on_history(out, card, gap=2060)
        self.assertEqual(status2, "same")
        self.assertEqual(out2[-1]["mental"]["determination"], 14)

    def test_score_prefers_nearest_continuing_card_over_far_high_b23(self):
        """Seimen regression: max-b23 favourite sat farther with Cmp=14."""
        mental_cmp13 = [*TIP_MENTAL[:12], 13, TIP_MENTAL[13]]
        mental_cmp14 = [*TIP_MENTAL[:12], 14, TIP_MENTAL[13]]
        near_newer = _synth_attr_card(mental=mental_cmp13, u16=100, b23=32)
        far_stale = _synth_attr_card(mental=mental_cmp14, u16=100, b23=253)
        tip = mod._ca_point_from_rec(near_newer)
        assert tip is not None
        pad = bytes([0x11] * 2_000)
        # Older/farther high-b23 Cmp=14 card, then nearer Cmp=13.
        window = far_stale + pad + near_newer + bytes([0x11] * 2_500)
        scored = mod.score_attr_window(window, tip=tip)
        self.assertIsNotNone(scored)
        _q, _off, rec = scored
        mental = [round(x / 5) for x in rec[0:14]]
        self.assertEqual(mental[12], 13)  # composure
        self.assertEqual(rec[23], 32)

    def test_score_rejects_foreign_high_b23_decoy(self):
        tip_card = _synth_attr_card(mental=TIP_MENTAL, u16=100, b23=10)
        decoy = _synth_attr_card(
            mental=DECOY_MENTAL,
            physical=DECOY_PHYS,
            tech=25,
            u16=999,
            b23=50,
        )
        tip = mod._ca_point_from_rec(tip_card)
        assert tip is not None
        pad = bytes([0x11] * 2_000)
        window = tip_card + pad + decoy + bytes([0x11] * 2_500)
        scored = mod.score_attr_window(window, tip=tip)
        self.assertIsNotNone(scored)
        _q, _off, rec = scored
        mental = [round(x / 5) for x in rec[0:14]]
        self.assertEqual(mental[5], 14)
        self.assertEqual(mental[7], 6)

    def test_recovers_tech_wiped_nearer_card_with_newer_det(self):
        """Sipho regression: Det=15 live card had Technique 0 garbage tech tail."""
        tip_mental = [*TIP_MENTAL]
        tip_mental[5] = 14
        tip_mental[7] = 3
        live_mental = [*tip_mental]
        live_mental[5] = 15
        live_mental[7] = 4
        tip_card = _synth_attr_card(mental=tip_mental, tech=70, u16=100, b23=25)
        wiped_live = _synth_attr_card(
            mental=live_mental, tech=0, u16=101, b23=27
        )
        tip = mod._ca_point_from_rec(tip_card)
        assert tip is not None
        self.assertIsNone(mod._ca_point_from_rec(wiped_live))
        recovered = mod._ca_point_from_rec(wiped_live, tip=tip)
        assert recovered is not None
        self.assertEqual(recovered["mental"]["determination"], 15)
        self.assertEqual(recovered["mental"]["leadership"], 4)
        self.assertEqual(recovered["technical"]["technique"], 14)

        pad = bytes([0x11] * 2_000)
        window = tip_card + pad + wiped_live + bytes([0x11] * 2_500)
        history = mod.build_ca_history(window)
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[-1]["mental"]["determination"], 15)
        scored = mod.score_attr_window(window, tip=history[-1])
        self.assertIsNotNone(scored)
        _q, _off, rec = scored
        mental = [round(x / 5) for x in rec[0:14]]
        self.assertEqual(mental[5], 15)
        out, status = mod.ensure_live_ca_on_history(
            history[:-1] or [tip], wiped_live, gap=2_500
        )
        self.assertIn(status, ("appended", "same"))
        self.assertEqual(out[-1]["mental"]["determination"], 15)


if __name__ == "__main__":
    unittest.main()
