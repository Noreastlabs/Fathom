"""Focused proof for the detached Level 47 full-workbook candidate."""

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
import parallel_07_level047_whole_candidate as lane  # noqa: E402


class Level47CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = (ROOT / lane.TXT_REL).read_bytes()
        cls.pdf = (ROOT / lane.PDF_REL).read_bytes()
        cls.model = lane.build_candidate(txt_data=cls.txt, pdf_data=cls.pdf)

    def test_all_modules_color_chords_attacks_and_conflict(self) -> None:
        model = self.model
        self.assertEqual(model["module_sounding_tone_counts"], lane.EXPECTED_COUNTS)
        self.assertEqual(model["written_workload_sounding_tones"], 872)
        self.assertEqual(model["pdf_parity"]["structured_row_count"], 717)
        self.assertEqual(len(model["positions"]), 5)
        self.assertEqual([len(model["modules"][key]["cells"]) for key in ("A", "C", "D", "G", "H")],
                         [10, 10, 10, 15, 10])
        for key in ("A", "C", "D", "G", "H"):
            for cell in model["modules"][key]["cells"]:
                self.assertEqual(len(cell["events"]), 8)
                self.assertEqual(len(cell["raw_rows"]), 9)
        sites = model["modules"]["B"]["sites"]
        self.assertEqual(len(sites), 6)
        self.assertEqual(model["modules"]["B"]["pick_attack_count"], 48)
        for site in sites:
            events = [event for part in site["passes"] for event in part["events"]]
            self.assertEqual(len(events), 12)
            self.assertEqual(sum(event["new_pick_attack"] for event in events), 8)
        self.assertEqual(sites[3]["string"], "G")
        self.assertEqual(sites[3]["tab_sounding_resolution_tone"], "D")
        self.assertEqual(sites[3]["pdf_note_guide_resolution_tone"], "A")
        self.assertEqual(model["source_conflicts"][0]["printed_tab_contact"], "G7")
        self.assertEqual(len(model["modules"]["E"]["studies"]), 6)
        self.assertEqual(len(model["modules"]["F"]["cells"]), 4)
        self.assertEqual(len(model["modules"]["I"]["choruses"]), 3)
        self.assertEqual([len(block["events"]) for chorus in model["modules"]["I"]["choruses"]
                          for block in chorus["blocks"]], [16] * 9)
        self.assertEqual(len(model["modules"]["J"]["recovery_cards"]), 12)
        self.assertEqual(model["modules"]["J"]["model_chorus"]["note_count"], 48)
        self.assertTrue(all(event["string"] is None for card in model["modules"]["J"]["recovery_cards"]
                            for event in card["sounds"]))
        self.assertFalse(model["runtime_eligible"])
        self.assertFalse(model["runtime_admitted"])
        self.assertIsNone(model["onset_q"])
        self.assertIsNone(model["canonical_item_id"])

    def test_source_drift_and_musical_parity_refused(self) -> None:
        changed = self.txt.replace(b"Col|C---M---C---m---", b"Col|C---m---C---m---", 1)
        with self.assertRaisesRegex(lane.CandidateError, "PINNED_INPUT_DRIFT L47-TXT"):
            lane.build_candidate(txt_data=changed, pdf_data=self.pdf)
        with patch.object(lane, "TXT_SHA256", hashlib.sha256(changed).hexdigest()):
            with self.assertRaisesRegex(lane.CandidateError, "PDF_TXT_STRUCTURED_ROWS_MISMATCH"):
                lane.build_candidate(txt_data=changed, pdf_data=self.pdf)
        with patch.object(lane, "TXT_SHA256", hashlib.sha256(changed).hexdigest()), patch.object(
                lane, "_verify_pdf_rows", return_value=self.model["pdf_parity"]):
            with self.assertRaisesRegex(lane.CandidateError, "STAFF_SLOT_INVALID"):
                lane.build_candidate(txt_data=changed, pdf_data=self.pdf)
        with self.assertRaisesRegex(lane.CandidateError, "PINNED_INPUT_DRIFT L47-PDF"):
            lane.build_candidate(txt_data=self.txt, pdf_data=self.pdf + b"x")
        pages = lane._pdf_pages(self.pdf)
        broken = deepcopy(pages)
        index = next(i for i, row in enumerate(broken[2]) if row.startswith("Col|"))
        broken[2][index] = broken[2][index].replace("M---", "m---", 1)
        with patch.object(lane, "_pdf_pages", return_value=broken):
            with self.assertRaisesRegex(lane.CandidateError, "PDF_TXT_STRUCTURED_ROWS_MISMATCH"):
                lane.build_candidate(txt_data=self.txt, pdf_data=self.pdf)

    def test_determinism_and_output_boundary(self) -> None:
        expected = (json.dumps(self.model, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
        output = ROOT / lane.BUILD_REL / "candidate.json"
        self.assertEqual(output.read_bytes(), expected)
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
