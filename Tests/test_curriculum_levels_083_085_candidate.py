"""Focused source and musical-fact checks for detached Levels 83–85 cells."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


TOOL = Path(__file__).resolve().parents[1] / "Tools/curriculum_levels_083_085_candidate.py"
spec = importlib.util.spec_from_file_location("curriculum_levels_083_085_candidate", TOOL)
assert spec and spec.loader
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = candidate.read_sources()
        cls.payload = candidate.build()

    def test_pinned_pairs_and_selected_pages(self) -> None:
        self.assertEqual(set(self.payload["levels"]), {"83", "84", "85"})
        for level, page in ((83, 10), (84, 2), (85, 4)):
            identities = self.payload["source_identities"][str(level)]
            self.assertEqual(set(identities), {"txt", "pdf"})
            self.assertEqual(self.payload["levels"][str(level)]["selected_pdf_page"]["page"], page)
            self.assertEqual(len(self.payload["levels"][str(level)]["cells"]), 6)

    def test_common_tone_roles_and_txt_lines(self) -> None:
        rows = self.payload["levels"]["83"]["cells"]
        self.assertEqual([r["fixed_melody"] for r in rows], list("EGCFBA"))
        self.assertEqual([r["txt_line"] for r in rows], list(range(37, 43)))
        for row in rows:
            for chord, role in zip(row["harmony"], row["printed_roles"]):
                candidate.check_role(row["fixed_melody"], chord, role)
            self.assertIsNone(row["bass_and_inner_voice_realization"])
            self.assertIsNone(row["onsets_and_durations"])

    def test_bad_pitch_role_rejected(self) -> None:
        with self.assertRaises(candidate.CandidateError):
            candidate.check_role("F", "G7", "3")
        with self.assertRaises(candidate.CandidateError):
            candidate.check_role("C", "Cmaj7", "b7")

    def test_outer_voices_preserve_order_without_timing(self) -> None:
        rows = self.payload["levels"]["84"]["cells"]
        self.assertEqual(rows[0]["bass_notes"], ["C", "B", "A", "G"])
        self.assertEqual(rows[3]["top_melody_notes"], ["F", "F#", "G#", "C"])
        self.assertEqual([r["txt_module_anchor_line"] for r in rows], [17] * 6)
        for row in rows:
            self.assertEqual(row["txt_cell_detail"], "omitted")
            self.assertEqual(len(row["bass_notes"]), 4)
            self.assertEqual(len(row["top_melody_notes"]), 4)
            self.assertIsNone(row["onsets_and_durations"])

    def test_note_length_labels_are_not_measured_durations(self) -> None:
        rows = self.payload["levels"]["85"]["cells"]
        self.assertEqual([r["printed_duration_target"] for r in rows],
                         ["100%", "75%", "50%", "25%", "percussive", "mixed"])
        self.assertEqual([r["txt_module_anchor_line"] for r in rows], [13] * 6)
        self.assertEqual([r["txt_practice_anchor_line"] for r in rows], [25] * 6)
        for row in rows:
            self.assertEqual(row["txt_cell_detail"], "omitted")
            self.assertIsNone(row["measured_sounding_duration"])
            self.assertIsNone(row["audio_timing"])

    def test_drift_and_malformed_tables_fail_closed(self) -> None:
        with self.assertRaises(candidate.CandidateError):
            candidate.exact_line(["x", "x"], "x")
        with self.assertRaises(candidate.CandidateError):
            candidate.bounded_table("A\n1\n2\nEND", "A\n", "END", 3, 1)
        with self.assertRaises(candidate.CandidateError):
            candidate.split_notes("C-E-G")
        modified = dict(self.sources[85])
        modified["pdf"] = dict(modified["pdf"])
        modified["pdf"]["content"] = list(modified["pdf"]["content"])
        modified["pdf"]["content"][3] = modified["pdf"]["content"][3].replace("100%", "90%")
        with self.assertRaises(candidate.CandidateError):
            candidate.level85(modified)

    def test_candidate_remains_detached(self) -> None:
        self.assertEqual(self.payload["status"], "Pending")
        self.assertEqual(self.payload["review"], "Pending")
        self.assertFalse(self.payload["canonical_ids_allocated"])
        self.assertFalse(self.payload["runtime_eligible"])
        self.assertFalse(self.payload["whole_workbook_complete"])
        self.assertEqual(self.payload["selected_cell_count"], 18)


if __name__ == "__main__":
    unittest.main()
