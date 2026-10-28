"""Focused source and musical-structure checks for Level 90 Module B."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


TOOL = Path(__file__).resolve().parents[1] / "Tools/curriculum_level090_music_candidate.py"
spec = importlib.util.spec_from_file_location("curriculum_level090_music_candidate", TOOL)
assert spec and spec.loader
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = candidate.read_source()
        cls.payload = candidate.build()
        cls.module = cls.payload["module_b"]

    def test_exact_source_pair_and_complete_selected_module(self) -> None:
        self.assertEqual(set(self.payload["source_identities"]), {"txt", "pdf"})
        self.assertEqual([p["page"] for p in self.module["selected_pdf_pages"]], [5, 6])
        self.assertEqual(len(self.module["shuffle_pattern_cells"]), 6)
        self.assertEqual(len(self.module["swing_shuffle_contrast_passes"]), 5)
        self.assertEqual(self.module["selected_cell_count"], 11)

    def test_six_patterns_preserve_two_triplet_groups(self) -> None:
        rows = self.module["shuffle_pattern_cells"]
        self.assertEqual(rows[0]["ordered_triplet_groups"], [["P", "-", "P"], ["P", "-", "P"]])
        self.assertEqual(rows[1]["ordered_triplet_groups"], [["M", "-", "O"], ["M", "-", "O"]])
        self.assertEqual(rows[4]["ordered_triplet_groups"], [[">P", "-", "P"], ["P", "-", ">P"]])
        self.assertEqual(rows[5]["ordered_triplet_groups"], [["P", "-", "P"], ["P", "P", "P"]])
        self.assertEqual([r["txt_module_anchor_line"] for r in rows], [11] * 6)
        self.assertEqual([r["txt_skill_anchor_line"] for r in rows], [23] * 6)
        for row in rows:
            self.assertEqual(row["txt_cell_detail"], "omitted")
            self.assertIsNone(row["performed_onsets_and_durations"])
            self.assertIsNone(row["swing_ratio"])

    def test_five_passes_retain_same_four_chord_progression(self) -> None:
        rows = self.module["swing_shuffle_contrast_passes"]
        self.assertEqual([r["printed_same_progression"] for r in rows], ["A7-D7-E7-A7"] * 5)
        self.assertEqual(rows[0]["ordered_chords"], ["A7", "D7", "E7", "A7"])
        self.assertEqual(rows[-1]["printed_instruction"], "return to jazz swing without changing tempo")
        self.assertEqual([r["txt_module_anchor_line"] for r in rows], [11] * 5)
        self.assertEqual([r["txt_skill_anchor_line"] for r in rows], [23] * 5)
        for row in rows:
            self.assertEqual(row["txt_cell_detail"], "omitted")
            self.assertIsNone(row["performed_onsets_and_durations"])
            self.assertIsNone(row["audio"])

    def test_invalid_pattern_and_progression_are_refused(self) -> None:
        for value in ("P - P P - P", "P - Q | P - P", "- - - | - - -", "P - P | P -"):
            with self.subTest(value=value), self.assertRaises(candidate.CandidateError):
                candidate.pattern_groups(value)
        for value in ("A7-D7-E7-G7", "A7-D7-E7", "A7-X7-E7-A7"):
            with self.subTest(value=value), self.assertRaises(candidate.CandidateError):
                candidate.progression_chords(value)

    def test_mutated_original_bytes_are_refused(self) -> None:
        for kind in ("txt", "pdf"):
            path, size, digest = candidate.SOURCE[kind]
            raw = (candidate.ROOT / path).read_bytes()
            candidate.verify_bytes(raw, size, digest, kind)
            changed = raw[:-1] + bytes([raw[-1] ^ 1])
            with self.assertRaises(candidate.CandidateError):
                candidate.verify_bytes(changed, size, digest, kind)

    def test_selected_pdf_cell_mutation_is_refused(self) -> None:
        changed = dict(self.source)
        changed["pdf"] = dict(changed["pdf"])
        changed["pdf"]["content"] = list(changed["pdf"]["content"])
        changed["pdf"]["content"][4] = changed["pdf"]["content"][4].replace("P - P | P - P", "P - Q | P - P")
        with self.assertRaises(candidate.CandidateError):
            candidate.module_b(changed)

    def test_status_remains_pending_and_unadmitted(self) -> None:
        self.assertEqual(self.payload["selected_cell_count"], 11)
        self.assertEqual(self.payload["status"], "Pending")
        self.assertEqual(self.payload["review"], "Pending")
        self.assertFalse(self.payload["canonical_ids_allocated"])
        self.assertFalse(self.payload["runtime_eligible"])
        self.assertFalse(self.payload["whole_workbook_complete"])
        self.assertIn("Pending", self.module["symbol_execution_semantics"])


if __name__ == "__main__":
    unittest.main()
