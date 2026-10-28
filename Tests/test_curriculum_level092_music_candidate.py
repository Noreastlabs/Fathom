"""Focused source and relationship checks for Level 92 Module A rake cells."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


TOOL = Path(__file__).resolve().parents[1] / "Tools/curriculum_level092_music_candidate.py"
spec = importlib.util.spec_from_file_location("curriculum_level092_music_candidate", TOOL)
assert spec and spec.loader
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = candidate.read_source()
        cls.payload = candidate.build()
        cls.module = cls.payload["module_a"]

    def test_pinned_pair_and_selected_page_contract(self) -> None:
        self.assertEqual(set(self.payload["source_identities"]), {"txt", "pdf"})
        self.assertEqual(self.module["selected_pdf_page"]["page"], 3)
        self.assertEqual(self.module["selected_pdf_rows"], "1-8")
        self.assertEqual(len(self.module["cells"]), 8)
        self.assertEqual(self.module["printed_intro"], candidate.INTRO)
        self.assertIn("three registers", self.module["printed_practice_instruction"])

    def test_contact_counts_and_string_targets(self) -> None:
        rows = self.module["cells"][:3]
        self.assertEqual([r["relationship"]["printed_muted_string_count"] for r in rows], [3, 4, 2])
        self.assertEqual([r["printed_target"] for r in rows],
                         ["B-string target", "high-e target", "G-string target"])
        self.assertEqual([r["relationship"]["printed_direction"] for r in rows],
                         ["low-to-high", "low-to-high", "high-to-low"])
        for row in rows:
            self.assertEqual(row["relationship"]["printed_event_order"],
                             ["muted strings", "pitched target"])

    def test_order_and_placement_remain_source_instructions(self) -> None:
        rows = self.module["cells"]
        self.assertEqual(rows[3]["relationship"]["printed_event_order"], ["rake ends", "bend begins"])
        self.assertEqual(rows[4]["relationship"]["printed_event_order"], ["pitch centers", "vibrato begins"])
        self.assertEqual([r["relationship"]["target_placement"] for r in rows[5:]],
                         ["next 16th", "beat", "beat 4"])
        self.assertEqual([r["relationship"]["printed_muted_string_count"] for r in rows[5:]],
                         [1, 2, None])
        self.assertEqual(rows[7]["relationship"]["printed_event_order"],
                         ["silent rest", "rake", "target"])
        for row in rows:
            self.assertEqual((row["txt_module_anchor_line"], row["txt_skill_anchor_line"]), (13, 25))
            self.assertEqual(row["txt_cell_detail"], "omitted")
            self.assertIsNone(row["performed_pitch_or_target_attainment"])
            self.assertIsNone(row["performed_muting_or_dynamics"])
            self.assertIsNone(row["performed_timing"])
            self.assertIsNone(row["audio_or_physical_result"])

    def test_mismatched_printed_relationships_are_refused(self) -> None:
        cases = ((1, "low-to-high", "B-string target", "4 muted strings + target"),
                 (3, "high-to-low", "B-string target", "2 muted strings + target"),
                 (4, "low-to-high", "bent target", "bend begins before rake ends"),
                 (5, "low-to-high", "vibrato target", "vibrato begins before pitch centers"),
                 (8, "silent rest -> rake", "target on beat 3", "dramatic entry"))
        for case in cases:
            with self.subTest(case=case), self.assertRaises(candidate.CandidateError):
                candidate.relationship(*case)

    def test_mutated_original_bytes_are_refused(self) -> None:
        for kind in ("txt", "pdf"):
            path, size, digest = candidate.SOURCE[kind]
            raw = (candidate.ROOT / path).read_bytes()
            candidate.verify_bytes(raw, size, digest, kind)
            changed = raw[:-1] + bytes([raw[-1] ^ 1])
            with self.assertRaises(candidate.CandidateError):
                candidate.verify_bytes(changed, size, digest, kind)

    def test_selected_cell_and_txt_anchor_mutations_are_refused(self) -> None:
        changed = dict(self.source)
        changed["pdf"] = dict(changed["pdf"])
        changed["pdf"]["content"] = list(changed["pdf"]["content"])
        changed["pdf"]["content"][2] = changed["pdf"]["content"][2].replace(
            "target on beat 4", "target on beat 3", 1)
        with self.assertRaises(candidate.CandidateError):
            candidate.module_a(changed)
        changed = dict(self.source)
        changed["txt"] = dict(changed["txt"])
        changed["txt"]["content"] = list(changed["txt"]["content"])
        changed["txt"]["content"][24] = "- uncontrolled rakes"
        with self.assertRaises(candidate.CandidateError):
            candidate.module_a(changed)

    def test_pending_unadmitted_status(self) -> None:
        self.assertEqual(self.payload["selected_cell_count"], 8)
        self.assertEqual(self.payload["status"], "Pending")
        self.assertEqual(self.payload["review"], "Pending")
        self.assertFalse(self.payload["canonical_ids_allocated"])
        self.assertFalse(self.payload["runtime_eligible"])
        self.assertFalse(self.payload["whole_workbook_complete"])


if __name__ == "__main__":
    unittest.main()
