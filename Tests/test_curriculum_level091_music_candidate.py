"""Focused source and interval checks for Level 91 bend-intonation cells."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


TOOL = Path(__file__).resolve().parents[1] / "Tools/curriculum_level091_music_candidate.py"
spec = importlib.util.spec_from_file_location("curriculum_level091_music_candidate", TOOL)
assert spec and spec.loader
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = candidate.read_source()
        cls.payload = candidate.build()
        cls.module = cls.payload["module_a"]

    def test_pinned_pair_and_visually_selected_page_contract(self) -> None:
        self.assertEqual(set(self.payload["source_identities"]), {"txt", "pdf"})
        self.assertEqual(self.module["supporting_calibration_page"]["page"], 2)
        self.assertEqual(self.module["selected_pdf_page"]["page"], 3)
        self.assertEqual(self.module["selected_cell_count"], 8)
        self.assertEqual(len(self.module["cells"]), 8)

    def test_reference_intervals_and_examples_agree(self) -> None:
        refs = self.module["calibration_reference"]
        self.assertEqual({key: int(value["printed_semitones"]) for key, value in refs.items()},
                         {"Half": 1, "Whole": 2, "1.5 step": 3})
        rows = self.module["cells"]
        self.assertEqual([r["printed_example"] for r in rows],
                         ["B8 -> B9", "B8 -> B10", "B8 -> B11", "G7 -> G8", "G7 -> G9",
                          "e8 -> e10", "e10 -> e13", "B10 -> B11"])
        self.assertEqual([r["reference_semitones"] for r in rows], [1, 2, 3, 1, 2, 2, 3, 1])
        self.assertEqual(rows[-1]["printed_task"], "half-step + 2-beat hold")
        self.assertEqual(rows[-1]["printed_additional_instruction"], "2-beat hold")
        for row in rows:
            self.assertEqual(row["target_reference_fret"] - row["source_fret"], row["reference_semitones"])
            self.assertEqual(row["txt_module_anchor_line"], 10)
            self.assertEqual(row["txt_skill_anchor_line"], 22)
            self.assertEqual(row["txt_cell_detail"], "omitted")
            self.assertIsNone(row["actual_target_pitch"])
            self.assertIsNone(row["bend_curve"])
            self.assertIsNone(row["performed_arrival_and_hold_timing"])
            self.assertIsNone(row["audio_or_physical_result"])

    def test_mismatched_intervals_and_strings_are_refused(self) -> None:
        refs = self.module["calibration_reference"]
        for example, task in (("B8 -> B10", "half-step"),
                              ("B8 -> G9", "half-step"),
                              ("e10 -> e13", "whole-step"),
                              ("B10 -> B11", "half-step + 3-beat hold")):
            with self.subTest(example=example, task=task), self.assertRaises(candidate.CandidateError):
                candidate.parse_example(example, task, refs)

    def test_mutated_original_bytes_are_refused(self) -> None:
        for kind in ("txt", "pdf"):
            path, size, digest = candidate.SOURCE[kind]
            raw = (candidate.ROOT / path).read_bytes()
            candidate.verify_bytes(raw, size, digest, kind)
            changed = raw[:-1] + bytes([raw[-1] ^ 1])
            with self.assertRaises(candidate.CandidateError):
                candidate.verify_bytes(changed, size, digest, kind)

    def test_selected_cell_mutation_is_refused(self) -> None:
        changed = dict(self.source)
        changed["pdf"] = dict(changed["pdf"])
        changed["pdf"]["content"] = list(changed["pdf"]["content"])
        changed["pdf"]["content"][2] = changed["pdf"]["content"][2].replace("B8 -> B9", "B8 -> B10", 1)
        with self.assertRaises(candidate.CandidateError):
            candidate.module_a(changed)

    def test_calibration_reference_mutation_is_refused(self) -> None:
        changed = list(self.source["pdf"]["content"])
        changed[1] = changed[1].replace("Half\n1\n", "Half\n2\n", 1)
        with self.assertRaises(candidate.CandidateError):
            candidate.calibration(changed)

    def test_pending_unadmitted_status(self) -> None:
        self.assertEqual(self.payload["selected_cell_count"], 8)
        self.assertEqual(self.payload["status"], "Pending")
        self.assertEqual(self.payload["review"], "Pending")
        self.assertFalse(self.payload["canonical_ids_allocated"])
        self.assertFalse(self.payload["runtime_eligible"])
        self.assertFalse(self.payload["whole_workbook_complete"])


if __name__ == "__main__":
    unittest.main()
