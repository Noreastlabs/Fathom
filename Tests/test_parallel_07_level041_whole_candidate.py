"""Focused source, route, parity, and safety proof for detached Level 41."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel_07_level041_whole_candidate as lane  # noqa: E402


class Level41CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = (ROOT / lane.TXT_REL).read_bytes()
        cls.pdf = (ROOT / lane.PDF_REL).read_bytes()
        cls.model = lane.build_candidate(txt_data=cls.txt, pdf_data=cls.pdf)

    def test_all_four_modules_and_prompts(self) -> None:
        model = self.model
        modules = model["modules"]
        self.assertEqual(model["written_workout_note_count"], 420)
        self.assertEqual([modules[name]["note_count"] for name in (
            "vertical_positions", "shared_anchor_seams", "linked_zigzag", "parallel_color_comparisons"
        )], [120, 120, 120, 60])
        positions = modules["vertical_positions"]["positions"]
        self.assertEqual([position["fret_span"] for position in positions],
                         [[5, 8], [7, 10], [9, 13], [12, 15], [14, 17]])
        self.assertEqual([position["starting_degree"] for position in positions],
                         ["1", "b3", "4", "5", "b7"])
        for position in positions:
            self.assertEqual(len(position["events"]), 24)
            self.assertEqual(len(position["string_pairs"]), 6)
            self.assertEqual(position["events"][11]["tone"], position["events"][12]["tone"])
            self.assertEqual(position["events"][11]["string"], position["events"][12]["string"])
            self.assertEqual(position["events"][11]["fret"], position["events"][12]["fret"])
            self.assertEqual(lane._normalized_rows(position["raw_rows"]),
                             lane._normalized_rows(position["pdf_raw_rows"]))
        for seam in modules["shared_anchor_seams"]["seams"]:
            self.assertEqual(len(seam["events"]), 30)
            self.assertEqual(seam["anchor_contact_slots"], [2, 4])
            self.assertEqual(seam["frame_phase_by_slot"],
                             ["lower", "lower", "upper", "upper", "lower"])
            for group in range(6):
                events = seam["events"][group * 5:(group + 1) * 5]
                self.assertEqual((events[1]["string"], events[1]["fret"]),
                                 (events[3]["string"], events[3]["fret"]))
        zigzag = modules["linked_zigzag"]
        self.assertEqual([part["direction"] for part in zigzag["forward"]["route"]],
                         ["asc", "desc", "asc", "desc", "asc"])
        self.assertEqual([part["direction"] for part in zigzag["reverse"]["route"]],
                         ["desc", "asc", "desc", "asc", "desc"])
        self.assertEqual(zigzag["turn_rearticulated"], "e17")
        self.assertEqual((zigzag["reverse"]["route"][-1]["events"][-1]["string"],
                          zigzag["reverse"]["route"][-1]["events"][-1]["fret"]), ("E", 5))
        pairs = modules["parallel_color_comparisons"]["pairs"]
        self.assertEqual(len(pairs), 5)
        for pair in pairs:
            self.assertEqual([len(p["events"]) for p in pair["phrases"]], [6, 6])
            self.assertTrue(pair["pdf_raw_rows"][1].startswith("Job|"))
            self.assertEqual(pair["silence_between_phrases_beats"], 1)
        self.assertEqual(len(model["random_entry_cards"]), 10)
        self.assertTrue(all(card["authored_phrase_events"] is None and
                            not card["counted_in_written_workout"] for card in model["random_entry_cards"]))
        self.assertTrue(all(card["required_resolution"]["tone"] == "A" for card in model["random_entry_cards"]))
        self.assertFalse(model["runtime_eligible"])
        self.assertFalse(model["runtime_admitted"])
        self.assertIsNone(model["canonical_item_id"])
        self.assertIsNone(model["onset_q"])

    def test_pinned_source_and_semantic_drift_refused(self) -> None:
        damaged = self.txt.replace(b"G5 (C / b3)", b"G6 (C / b3)", 1)
        with self.assertRaisesRegex(lane.CandidateError, "PINNED_INPUT_DRIFT L41-TXT"):
            lane.build_candidate(txt_data=damaged, pdf_data=self.pdf)
        with patch.object(lane, "TXT_BYTES", len(damaged)), patch.object(
                lane, "TXT_SHA256", hashlib.sha256(damaged).hexdigest()):
            with self.assertRaisesRegex(lane.CandidateError, "RANDOM_CARD_PITCH_INVALID"):
                lane.build_candidate(txt_data=damaged, pdf_data=self.pdf)
        with self.assertRaisesRegex(lane.CandidateError, "PINNED_INPUT_DRIFT L41-PDF"):
            lane.build_candidate(txt_data=self.txt, pdf_data=self.pdf + b"x")
        pages = lane._pdf_pages(self.pdf)
        broken = deepcopy(pages)
        row = next(i for i, line in enumerate(broken[11]) if line.startswith("Job|"))
        broken[11][row] = broken[11][row].replace("b3--", "2---", 1)
        with patch.object(lane, "_pdf_pages", return_value=broken):
            with self.assertRaisesRegex(lane.CandidateError, "PDF_TXT_COLOR_STAFF_MISMATCH"):
                lane.build_candidate(txt_data=self.txt, pdf_data=self.pdf)

    def test_output_determinism_and_confinement(self) -> None:
        data = (json.dumps(self.model, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
        output = ROOT / lane.BUILD_REL / "candidate.json"
        self.assertEqual(output.read_bytes(), data)
        with self.assertRaisesRegex(lane.CandidateError, "OUTPUT_EXISTS"):
            lane.write_candidate(output)
        with tempfile.TemporaryDirectory() as tempdir:
            outside = Path(tempdir) / "candidate.json"
            with self.assertRaisesRegex(lane.CandidateError, "OUTPUT_OUTSIDE_LANE_BUILD"):
                lane.write_candidate(outside)
            link = ROOT / lane.BUILD_REL / "test-symlink.json"
            try:
                link.symlink_to(outside)
                with self.assertRaisesRegex(lane.CandidateError, "OUTPUT_INVALID"):
                    lane.write_candidate(link)
            finally:
                link.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
