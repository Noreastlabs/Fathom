"""Focused source, triad, count, and boundary proof for detached Level 52."""

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
import parallel_07_level052_whole_candidate as lane  # noqa: E402


class Level52CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = (ROOT / lane.TXT_REL).read_bytes()
        cls.pdf = (ROOT / lane.PDF_REL).read_bytes()
        cls.model = lane.build_candidate(txt_data=cls.txt, pdf_data=cls.pdf)

    def test_whole_workload_voicing_alternative_and_mastery(self) -> None:
        model = self.model
        modules = model["modules"]
        self.assertEqual(model["module_attack_counts"], lane.EXPECTED_COUNTS)
        self.assertEqual(model["sounded_workload_attack_count"], 976)
        self.assertEqual(model["silent_formation_count"], 42)
        shapes = modules["shape_workouts"]["shapes"]
        self.assertEqual(len(shapes), 42)
        self.assertEqual({(shape["root"], shape["quality"], shape["inversion"]) for shape in shapes}.__len__(), 42)
        for shape in shapes:
            self.assertEqual(len(shape["attacks"]), 10)
            self.assertEqual([a["kind"] for a in shape["attacks"]], ["blocked"] * 4 + ["arpeggio"] * 6)
            self.assertEqual([a["string"] for a in shape["attacks"][4:]], ["G", "B", "e", "e", "B", "G"])
        self.assertEqual(len(modules["inversion_cycles"]["cycles"]), 14)
        self.assertEqual(len(modules["quality_switches"]["switches"]), 21)
        alternates = [s for s in modules["quality_switches"]["switches"] if s["alternate_octave"]]
        self.assertEqual(len(alternates), 1)
        self.assertEqual(alternates[0]["major_frets_g_b_e"], [12, 13, 12])
        open_c = next(shape for shape in shapes if shape["chord"] == "C" and
                      shape["inversion"] == "second_inversion")
        self.assertEqual(open_c["frets_g_b_e"], [0, 1, 0])
        f6 = modules["patterns"]["patterns"][5]
        self.assertEqual(sum(a["sounded"] for a in f6["attacks"]), 4)
        self.assertEqual(sum(not a["sounded"] for a in f6["attacks"]), 4)
        self.assertEqual([a["kind"] for a in f6["attacks"]],
                         ["blocked", "muted_backbeat"] * 4)
        self.assertEqual(len(modules["major_progressions"]["progressions"]), 4)
        self.assertEqual(len(modules["minor_progressions"]["progressions"]), 4)
        self.assertEqual(len(modules["major_capstone"]["bars"]), 16)
        self.assertEqual(len(modules["minor_capstone"]["bars"]), 16)
        silent = modules["silent_and_ear_tasks"]
        self.assertEqual(len(silent["formations"]), 42)
        self.assertEqual(silent["pdf_first_attempt_threshold"],
                         {"minimum_correct_per_quality": 18, "total_per_quality": 21})
        self.assertEqual(silent["txt_mastery_separate_days"], 2)
        self.assertFalse(silent["counted_in_attacks"])
        self.assertFalse(model["runtime_eligible"])
        self.assertFalse(model["runtime_admitted"])
        self.assertIsNone(model["canonical_item_id"])
        self.assertIsNone(model["onset_q"])

    def test_pins_semantic_mutations_and_pdf_parity(self) -> None:
        changed = self.txt.replace(b"G-B-e frets: 5-5-3", b"G-B-e frets: 5-5-4", 1)
        with self.assertRaisesRegex(lane.CandidateError, "PINNED_INPUT_DRIFT L52-TXT"):
            lane.build_candidate(txt_data=changed, pdf_data=self.pdf)
        with patch.object(lane, "TXT_SHA256", hashlib.sha256(changed).hexdigest()):
            with self.assertRaisesRegex(lane.CandidateError, "TRIAD_SHAPE_MUSIC_INVALID"):
                lane.build_candidate(txt_data=changed, pdf_data=self.pdf)
        with self.assertRaisesRegex(lane.CandidateError, "PINNED_INPUT_DRIFT L52-PDF"):
            lane.build_candidate(txt_data=self.txt, pdf_data=self.pdf + b"x")
        pages = lane._pdf_pages(self.pdf)
        broken = deepcopy(pages)
        i = broken[12].index("MAJ|12-13-12|")
        broken[12][i] = "MAJ|0-1-0|"
        with patch.object(lane, "_pdf_pages", return_value=broken):
            with self.assertRaisesRegex(lane.CandidateError, "PDF_QUALITY_SWITCH_MISMATCH"):
                lane.build_candidate(txt_data=self.txt, pdf_data=self.pdf)

    def test_deterministic_bytes_and_output_confinement(self) -> None:
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
